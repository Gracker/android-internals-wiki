---
title: "耗电/发热伴随卡顿排障入口"
chapter: "7.16"
status: ready-for-review
drafted_date: "2026-05-18"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-07-30"
last_verified_against: "Perfetto docs + Android Developers power docs + AOSP android-17.0.0_r1 public paths + PowerManager API reference"
confidence: medium-high
tags: [jank, power, thermal, perfetto, battery-historian]
related_chapters: ["5.5", "5.10", "7.15", "11.1", "13.2", "14.11", "25.1", "25.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "章节深挖/研究素材/官方文档"
task6_state: fixed
task9_state: rework-verified
pipeline_stage: rework-verified
last_rework_at: "2026-07-30T09:37:01+08:00"
last_rework_run_id: "20260730-093701-rework-e61f2940"
rework_summary: "解决 pending-verification-marker（§四类场景入口将「待验证假设」改为「证据缺口记录」）和 thin-source-marking（正文新增 5 处 [来源:]/[已验证:] 内联证据标记，覆盖 ThermalManagerService、PowerManager.getThermalHeadroom、IPowerStats、FrameTimeline SurfaceView 边界和 ARR API）。frontmatter 新增 PowerManager API 与 thermal-mitigation 来源。"
path: "src/part2-performance/ch07-smoothness/16-power-thermal-jank-playbook.md"
sources:
  - type: official
    path: "https://perfetto.dev/docs/data-sources/battery-counters"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/cpu-freq"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: official
    path: "https://source.android.com/docs/core/power/thermal-mitigation"
  - type: official
    path: "https://source.android.com/docs/core/power/power-stats-hal"
  - type: official
    path: "https://developer.android.com/topic/performance/power/battery-historian"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls"
  - type: official
    path: "https://developer.android.com/reference/android/os/PowerManager"
  - type: official
    path: "https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl"
  - type: aosp
    path: "hardware/interfaces/thermal/aidl/android/hardware/thermal/"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java"
  - type: internal
    path: "intake/research-gaps.md#2026-05-17-7.15"
  - type: internal
    path: "src/part1-fundamentals/ch05-cpu-power/05-thermal.md"
  - type: internal
    path: "src/part5-app/ch25-power-size/01-power-diagnosis.md"
---

# 7.16 耗电/发热伴随卡顿排障入口

<!-- outline-start -->
## 要点

### 🔹 投诉入口拆分：掉帧、发热、掉电分别代表什么
把线上反馈拆成三类信号：用户看到的帧时间异常、设备进入热限制后的频率收缩、后台任务或网络重试带来的持续耗电。加工时需要给出一张分流表，说明每类信号优先看哪些轨道和指标。

### 🔹 Perfetto 联合采集模板
覆盖 FrameTimeline、sched、CPU frequency、GPU/Display 相关 counter、thermal status、android.power、network packets、wakelock 事件。模板要说明哪些字段依赖设备暴露 power rails / ODPM，缺失时如何降级。

### 🔹 CPU/GPU 持续负载与热限制判读
区分短时峰值、持续满载、频率被动下降和调度迁移。加工时要把 thermal status、CPU/GPU 频率、top-app 线程运行时间和 FrameTimeline jank 对齐，避免只看单帧耗时。

### 🔹 Wakelock、JobScheduler/WorkManager 与网络重试
整理后台保活、周期任务、失败重试、前台服务和网络连接在 Battery Historian / batterystats / Perfetto 中的观察入口。与 5.10、25.2 交叉引用，不重复展开后台调度机制。

### 🔹 渲染负载、刷新率与显示功耗
说明高刷新率、复杂动画、视频/地图/WebView 页面如何同时影响帧时间和显示/SoC 能耗。加工时只写排障路径，渲染原理引用 2.x、18.x 章节。

### 🔹 设备能力差异与证据等级
列出 Pixel / AOSP 设备、厂商设备、低端机在 power rail、thermal HAL、GPU counter、网络 counter 可见性上的差异。没有设备级证据时标注证据缺口，不写泛化结论。

## 扩展

### 🔸 Power rail 命名与 EnergyConsumer 对照
整理 rail / channel、EnergyConsumer、BatteryUsageStats 三套口径之间的区别，作为 11.1 与 25.1 的补充索引。

### 🔸 热状态驱动的线上降级策略
补充根据 thermal status / thermal headroom 调整动画、刷新率、网络重试和后台任务节奏的策略，但需要标注 API 版本和设备限制。

### 🔸 游戏、地图、视频、WebView 四类场景案例
每类场景给出采集配置、第一判断点和常见误判，案例材料不足时保留为待补充。

<!-- outline-end -->

## 适用范围与排障目标

本章以 Android 17 / API 37 / `android-17.0.0_r1` 为平台源码锚点，内核事件以 `android17-6.18-2026-06_r6` 为准。厂商的温度阈值、传感器名称、功率预算、GPU 计数器和 power rail 属于设备实现，不能从 AOSP tag 推导某款量产机的具体数值。

“滑动卡、手机烫、掉电快”包含三种时间尺度：

- 帧或输入反馈通常以毫秒到秒衡量；
- 温升与 thermal mitigation 通常需要数十秒到数分钟；
- 后台耗电、WakeLock 和网络重试通常需要分钟到小时。

分析要把三种时间尺度放进同一份场景记录，又要分别选择合适的测量工具。短时 trace 适合还原一次帧超时；Batterystats 适合累计 UID 行为；稳定功耗比较还需要固定设备状态、环境和对照版本。

## 把用户反馈改写成可测量信号

| 用户反馈 | 要确认的信号 | 起始工具 | 不能直接得出的结论 |
|---|---|---|---|
| “滑动或动画卡” | 哪些 SurfaceFrame/DisplayFrame 超时，哪条线程或合成路径位于关键区间 | FrameTimeline、主线程、RenderThread、SurfaceFlinger、sched | 一帧红色不能解释长时间掉电 |
| “越用越烫，后来变卡” | 负载是否持续；thermal severity、cooling state 或频率限制是否在卡顿前变化 | `ThermalManagerService.status`、thermal/cpufreq 轨道、FrameTimeline | 低频本身不能证明 thermal throttling |
| “不操作也掉电” | 灭屏期间 UID 是否持有 WakeLock、运行 Job、定位或反复联网 | Batterystats、bugreport、Battery Historian、业务日志 | 电量百分比下降不能定位线程或请求 |
| “页面一开就卡又耗电” | 渲染、网络、解码、数据库和第三方组件是否在同一窗口争用资源 | Perfetto、应用 marker、power rails、网络日志 | rail 上升不能直接归到一个 Java 方法 |
| “只在某些机型出现” | 设备能力、thermal 策略、HWC、刷新率和后台环境是否不同 | 设备样本表与同场景对照 | 单台设备的阈值不能推广到其他 SoC |

问题卡至少要记录：应用 commit、设备 fingerprint、内核版本、环境温度、电量与充电状态、亮度、刷新率、网络类型、场景脚本、起止时间和复现率。缺少这些条件，两次“相同测试”可能处于完全不同的功率和温控状态。

## 先区分控制平面与报告平面

thermal 现场常同时出现两条路径。

控制平面负责限制发热源，位置可能在硬件、固件、Linux thermal core 或 vendor 服务：

```text
传感器/估算模型
  → thermal zone 或厂商策略
  → cooling device、功率预算、频率/容量上限
  → CPU、GPU、显示、充电或无线子系统减载
```

这条路径可以在 Framework 收到通知前开始动作。`thermal engine` 进程名、配置文件位置和控制算法没有跨厂商统一约定。

报告平面把热压力交给 Android Framework 和应用：

```text
传感器与设备策略
  → Thermal HAL
  → ThermalManagerService
  → PowerManager thermal status/headroom
  → 系统组件与应用按状态减载
```

Android 17 的 `ThermalManagerService` 位于 `frameworks/base/services/core/java/com/android/server/power/thermal/`。AOSP 源码会从缓存的 SKIN 类型温度中取最高 throttling severity，更新整体 status，并通过 `TRACE_TAG_POWER` 写入名为 `ThermalManagerService.status` 的 counter。启用 `power` atrace 类别后，这条 counter 是 Framework 热状态与 Perfetto 对齐的重要入口。[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/thermal/ThermalManagerService.java]

整体 status 表达面向用户体验的 thermal severity。它不等于 CPU 温度，也不承诺映射到固定 GHz、固定 GPU 档位或某个 cooling device state。详细传感器数据由 Thermal HAL 面向可信系统组件提供；普通应用使用公开的 `PowerManager` 状态和 headroom API。

## Android 10—17 的公开 thermal 入口

| API | 起始版本 | 含义与边界 |
|---|---:|---|
| `getCurrentThermalStatus()` | API 29 | 当前整体 thermal severity，范围为 `NONE` 到 `SHUTDOWN` |
| `addThermalStatusListener()` | API 29 | severity 变化回调；回调时间不等于硬件开始限功率的时间 |
| `getThermalHeadroom(seconds)` | API 30 | 慢变化传感器距离 `SEVERE` 阈值的预测；参数范围 0—60 秒 |
| `getThermalHeadroomThresholds()` | API 35 | status 到 headroom threshold 的设备映射；可能不含全部 status |
| `addThermalHeadroomListener()` | API 36 | headroom 或 thresholds 变化回调 |

`getThermalHeadroom()` 返回非负值，`1.0` 对应 `SEVERE` threshold；大于 `1.0` 没有统一的更高 severity 映射。不支持、服务未准备好或调用过密时可能得到 `NaN`。官方 API 文档说明这类慢变化传感器没有必要以高于约每秒一次的频率轮询。[来源: developer.android.com/reference/android/os/PowerManager#getThermalHeadroom(int)]

API 35 的 thresholds 来自设备配置。API 36 起 thresholds 可发生变化，可通过 headroom listener 获知。应用应保存 status、headroom、thresholds、时间戳和设备身份，不要把自定的 `0.8` 之类阈值写成平台常量。

## Perfetto 联合采集

### 采集前检查设备能提供什么

在正式场景前抓一份 10 秒探测 trace，检查以下轨道是否存在：

- `ThermalManagerService.status`；
- thermal zone 温度、trip 和 cooling-device 更新；
- CPU frequency、frequency limits 与 idle；
- GPU frequency/devfreq；
- battery counters；
- power rails、energy consumer breakdown、entity state residency；
- FrameTimeline；
- kernel wakeup source。

轨道缺失可能由 HAL 未实现、硬件不支持、内核 tracepoint 未启用、SELinux/权限、厂商裁剪或采集配置造成。缺轨时先标记能力缺口，再选择替代证据。

### Android 17 配置模板

下面的 textproto 用于 120 秒前台“高负载 → 温升 → 卡顿”场景。字段均可在 Android 17 对应的 Perfetto config proto 中找到；包名需要换成目标应用：

```protobuf
buffers {
  size_kb: 131072
  fill_policy: RING_BUFFER
}
duration_ms: 120000

data_sources {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}

data_sources {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_waking"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_frequency_limits"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "power/wakeup_source_activate"
      ftrace_events: "power/wakeup_source_deactivate"
      ftrace_events: "thermal/thermal_temperature"
      ftrace_events: "thermal/thermal_zone_trip"
      ftrace_events: "thermal/cdev_update"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "freq"
      atrace_categories: "power"
      atrace_categories: "wm"
      atrace_apps: "com.example.app"
    }
  }
}

data_sources {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      cpufreq_period_ms: 500
      gpufreq_period_ms: 500
      devfreq_period_ms: 500
      thermal_period_ms: 1000
    }
  }
}

data_sources {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 1000
      battery_counters: BATTERY_COUNTER_CAPACITY_PERCENT
      battery_counters: BATTERY_COUNTER_CHARGE
      battery_counters: BATTERY_COUNTER_CURRENT
      battery_counters: BATTERY_COUNTER_CURRENT_AVG
      battery_counters: BATTERY_COUNTER_VOLTAGE
      collect_power_rails: true
      collect_energy_estimation_breakdown: true
      collect_entity_state_residency: true
    }
  }
}

data_sources {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}

data_sources {
  config {
    name: "linux.system_info"
  }
}
```

`power/cpu_frequency` 记录变化事件，`cpufreq_period_ms` 补 trace 开始处的当前值；两者一起使用可减少误读。`gpufreq_period_ms`、`devfreq_period_ms`、thermal tracepoint 和 wakeup-source 轨道仍依赖设备。`collect_power_rails` 需要 ODPM/PowerStats HAL 的 energy-meter channel；另外两个开关分别请求 EnergyConsumer breakdown 与 PowerEntity state residency。[已验证: AOSP android-17.0.0_r1, hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl; perfetto.dev/docs/data-sources/battery-counters]

模板使用 128 MiB ring buffer，是为了容纳高频 sched 事件。若目标设备的 Perfetto guardrail 拒绝该大小，或采集本身改变了温控曲线，应缩短窗口、分开采集高频与低频数据，或改用 periodic snapshot；分析前还要在 trace `stats` 表检查 packet loss 和 buffer overwrite。

配置本身不包含通用的网络包归因。不同内核的网络 tracepoint 开销和权限差异很大，应用应给请求、重试、DNS 和响应增加 marker，并保留 OkHttp/Chromium/播放器等组件的事件日志；长窗口再用 Batterystats 的 UID 网络统计验证。

FrameTimeline 当前不覆盖 `SurfaceView` 内容帧。视频、相机和游戏若通过独立 Surface 输出，要补 Producer、BufferQueue、fence、SurfaceFlinger 与 HWC 证据，不能用宿主 App Window 的绿色帧代表内容层按时呈现。[已验证: perfetto.dev/docs/data-sources/frametimeline]

## 怎样证明 thermal throttling 影响了卡顿

一条可信的因果序列应包含以下阶段：

1. 场景开始后，目标进程或相关系统组件形成持续负载。
2. SKIN severity、thermal headroom、thermal zone、trip 或 cooling state 出现变化。
3. CPU/GPU 可用容量、policy 上限或请求频率受到约束。
4. 工作量和场景输入保持稳定时，线程运行时间、Runnable 等待、GPU completion 或帧时间变差。
5. 冷却设备、降低负载或恢复策略后，限制和性能退化按预测回落。

缺少第 2、3 项时，只能写“热场景下相关”。缺少稳定工作量或对照组时，频率下降也可能来自普通 DVFS。缺少回落过程时，还应排查电池电流限制、Power Saver、刷新率切换、后台争用和厂商 boost 策略。

### CPU 侧判读

| 轨道组合 | 候选解释 | 下一项证据 |
|---|---|---|
| 线程持续 Running，频率高，status 不变 | 工作量本身超预算 | 热点栈、业务 marker、帧关键路径 |
| 线程持续 Running，`cpu_frequency_limits` 上限下降，status/trip 同期上升 | thermal 或设备功率约束介入 | cooling state、设备策略、冷却对照 |
| 主线程持续 Runnable，频率和上限正常 | CPU 争抢或优先级问题 | 同核运行者、cgroup、线程池、Binder |
| 频率下降，CPU idle 增加 | 负载减少后的正常 DVFS | 业务工作量、唤醒频率 |
| 频率低但任务迁移到另一 cluster | 调度迁移或共享 policy | per-CPU 轨道、cluster policy、capacity |

频率只描述时钟。CPU capacity 还会受架构、idle、在线 CPU、调度约束和功率预算影响。不能用“利用率高 + 频率低”单独认定 thermal throttling。

### GPU 与显示侧判读

GPU 轨道在量产设备上的差异更大。可按证据强度分三层：

- 有 GPU frequency/busy、GPU completion、rail：检查负载、频率限制、完成时间和能量是否同窗变化。
- 有 RenderThread、fence、SurfaceFlinger，缺 GPU counter：结论写到“GPU/合成路径候选”，再做降分辨率、去特效或改变 Layer 的对照。
- 只有帧超时：保留 App、RenderThread、SurfaceFlinger 三路候选，不写 GPU 根因。

power rail 是设备级累计能量。其他应用、SurfaceFlinger、媒体和显示都可能贡献同一 rail；它适合做受控 A/B，不适合直接归因某个 shader 或方法。

## 渲染负载、刷新率与显示功耗

高刷新率同时缩短帧预算并增加显示更新机会。60 Hz 常见周期约 16.67 ms，120 Hz 约 8.33 ms；可变刷新率和 Android 15 引入的 Adaptive Refresh Rate 会改变运行时节奏，分析时应读取 trace 中的 Expected Timeline、VSync 与显示模式。

ARR 只在实现相应 HWC HAL 能力的 Android 15 QPR1+ 设备上可用。API 36 提供 `hasArrSupport()` 等公开能力查询。ARR 面板可在同一显示模式内按离散 VSync 步进调整刷新节奏，因此“当前模式是 120 Hz”不代表内容持续以 120 fps 产生或显示。[来源: developer.android.com/develop/ui/views/animations/adaptive-refresh-rate]

对普通 View/Compose Window，可沿 `Choreographer → RenderThread → BLAST BufferQueue → SurfaceFlinger → HWC → present` 对齐帧与功耗。`SurfaceView`、`TextureView`、WebView 和视频要按输出路径分流：

| 输出类型 | 帧证据 | 功耗排查重点 |
|---|---|---|
| 普通 View/Compose | App SurfaceFrame、DisplayFrame、主线程、RenderThread | 布局/绘制、纹理上传、GPU、显示 |
| `SurfaceView` | 独立 Layer、Producer、BufferQueue、fence、SF/HWC | 解码/渲染 Producer、overlay/client composition、显示 |
| `TextureView` | 外部 Buffer 更新 + 宿主 Window SurfaceFrame | 外部 Producer、宿主纹理采样、GPU 合成 |
| WebView | renderer 进程 + 宿主 functor/HWUI；媒体可能另有 Layer | JS/layout、图片、网络、renderer、宿主合成 |
| Flutter | Engine/应用线程、根渲染模式、平台视图、外部纹理 | raster/Engine、平台视图合成、GPU、线程模型 |

HWC 的 `DEVICE` composition 也不等于“没有功耗”；overlay plane、显示控制器和面板仍在工作。`CLIENT` composition 增加 GPU 合成的可能性，但能量差异必须在同设备、同画面、同亮度和同刷新率下测量。

## Wakelock、Job、前台服务与网络重试

亮屏高负载与灭屏后台要分开测试。亮屏窗口常由显示、CPU/GPU、解码、网络和定位共同贡献；灭屏窗口优先检查 CPU 是否进入 suspend、谁持有 Partial WakeLock、哪些 Job/Alarm/网络请求反复唤醒设备。

| 信号 | 长窗口入口 | 短窗口入口 | 常见代码方向 |
|---|---|---|---|
| Partial WakeLock 持有过久 | Batterystats、Battery Historian Userspace Wakelock | `dumpsys power`、power/wakeup-source trace | tag、释放路径、超时、组件生命周期 |
| Job/Work 反复运行 | JobScheduler/Sync 记录、UID CPU time | `dumpsys jobscheduler`、业务 marker | unique work、约束、退避、失败分类 |
| 前台服务常驻 | 进程/FGS 历史、通知与 UID 统计 | `dumpsys activity services` | 服务类型、用户可见任务、停止条件 |
| 网络短脉冲密集 | UID 网络字节、radio active | 请求 marker、重试日志、TrafficStats tag | 指数退避、批量、缓存、连接复用 |
| 定位/传感器持续 | GPS/Sensor 活跃时间 | Location/Sensor marker | 精度、频率、批处理、后台条件 |

应用没有直接调用 `PowerManager.newWakeLock()`，也可能因 WorkManager、JobScheduler、定位、音频或其他系统组件产生归因到该 UID 的 WakeLock 活动。要从 tag 和执行时间回到具体任务，不应只搜索直接 API 调用。

弱网重试要同时记录次数、间隔、传输量和 radio active。相同字节数下，密集短连接与批量传输的能量特征可能不同；请求是否位于交互路径，也决定它属于响应卡顿还是后台功耗。

## 长窗口 Batterystats 采集

Battery Historian 已不再活跃维护。官方建议优先考虑 System Trace、Macrobenchmark `PowerMetric` 或 Power Profiler；它仍可用于读取长窗口 bugreport 和历史项目。Power Profiler 官方支持范围以具有 ODPM 的设备为准，文档列出的常见入口是 Pixel 6 及后续 Pixel。

下面的命令用于建立一次干净的电池统计窗口。`--reset` 会清空现有 Batterystats 历史，执行前要确认旧数据不再需要：

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys batterystats --enable full-wake-history

# 断开 USB，执行固定时长的亮屏或灭屏场景；结束后重新连接。
adb bugreport bugreport-power.zip
adb shell dumpsys batterystats --charged > batterystats-charged.txt
adb shell dumpsys power > dumpsys-power.txt
adb shell dumpsys jobscheduler > dumpsys-jobscheduler.txt
```

USB 连接会改变充电状态，还可能让内核 USB 驱动持有 WakeLock，测试阶段应断开。`full-wake-history` 会增加历史记录量，长时间采样可能更快覆盖旧事件；只在需要逐事件查看 WakeLock 时开启。文本重定向发生在开发机上，输出文件要和 bugreport、场景日志使用同一命名规则。

长窗口报告要按 UID 解读 CPU time、WakeLock、network、GPS/sensor、Job、Sync 和 Alarm。Battery Historian 时间条表示组件何时活跃，不直接表示该组件消耗了多少能量；BatteryUsageStats 中的 mAh 也可能由 measured energy 或 power profile 模型生成，报告应注明 `power_model`。

## Power rail、EnergyConsumer 与 BatteryUsageStats

Android 17 的 AIDL `IPowerStats` 提供三组不同语义：

| PowerStats AIDL 对象 | 读取方法 | 数据语义 |
|---|---|---|
| Energy-meter `Channel` | `getEnergyMeterInfo()` / `readEnergyMeter()` | channel 自启动以来的累计能量、时间戳和累计时长；名称与 subsystem 对 Framework 不透明 |
| `EnergyConsumer` | `getEnergyConsumerInfo()` / `getEnergyConsumed()` | 逻辑消费者自启动以来的累计能量，可选 UID attribution |
| `PowerEntity` | `getPowerEntityInfo()` / `getStateResidency()` | 子系统各状态的驻留时间、进入次数与最近进入时间 |

Perfetto 的 `collect_power_rails` 对应可用的 energy-meter channels。`collect_energy_estimation_breakdown` 请求 EnergyConsumer 数据，`collect_entity_state_residency` 请求 PowerEntity 状态驻留。HAL 可以不提供某类数据，单次请求也不保证每个 entity 都有返回值。

`BatteryUsageStats` 位于 Framework 归因层，会组合设备测量、控制器活动、内核/UID 统计和 `power_profile.xml` 模型。它适合回答“哪个 UID 或组件在统计窗口内消耗较多”，不能代替毫秒级 rail 时间线。

三类常见误读需要避开：

- rail、consumer、entity 的 ID 和名称只在当前设备实现内解释；
- 累计能量要取区间差值，不能把启动以来的绝对值当作本次场景；
- ODPM/rail 是设备级测量，UID 归因需要额外模型或 attribution，二者不能直接画等号。

## 设备能力与证据等级

| 等级 | 已取得的证据 | 允许写出的判断 |
|---|---|---|
| A | 帧/响应时间线 + 线程调度 + CPU/GPU 约束 + thermal status/trip/cooling + rail/consumer + 对照 | 描述该设备、该构建、该窗口内的负载、热限制、性能与能量关系 |
| B | 帧/响应时间线 + sched + CPU frequency limits + thermal status/zone，缺能量轨道 | 判断 thermal/功率约束是否影响性能；不拆硬件域能量 |
| C | Batterystats + bugreport + 业务日志，缺短时 trace | 判断长窗口 UID 的 WakeLock、Job、网络、定位是否异常；不解释单帧 |
| D | 用户反馈、电量百分比或机身触感 | 作为复现线索；不写线程、thermal 或能量根因 |

每条结论都要带设备型号、fingerprint、内核、应用 commit、亮度、刷新率、电量、充电状态、网络、环境温度、场景时长和后台状态。跨设备比较 rail 绝对值时，还要确认采样点、单位、覆盖子系统和硬件采样率一致。

## 热状态驱动的可逆降载

降载策略分为“状态已升高后的响应”和“headroom 接近 threshold 的预备动作”。

| 触发信号 | 适合的动作 | 恢复条件 |
|---|---|---|
| `THERMAL_STATUS_LIGHT` | 停止无用户价值的预取、遥测和装饰动效 | status 回落并保持一段迟滞时间 |
| `MODERATE` | 降低非必要刷新、后台并发、网络重试频率 | status/headroom 恢复且场景仍活跃 |
| `SEVERE` 及以上 | 降帧率、分辨率、编码/推理复杂度，暂停可延后任务 | 逐级恢复，禁止一次跳回最高负载 |
| headroom 接近设备 threshold | 预加载低质量资源、准备切档，避免立即震荡 | listener 或轮询显示余量恢复 |

动作要满足四个条件：

1. 用户可理解，不能悄悄破坏录制、导航或通信等任务语义。
2. 可逆，并有迟滞，避免在阈值附近反复切换。
3. 按设备 API 能力降级；`NaN`、异常或空 thresholds 不能被当成安全余量。
4. 有线上指标，至少记录触发原因、档位、持续时间、退出原因和体验指标。

刷新率、画质、码率和网络并发应分别受控，便于通过 A/B 判断哪项动作改善了帧时间或能量。一次同时改变多个变量，只能证明组合有效，无法确认贡献来源。

## 四类场景入口

| 场景 | 采集重点 | 第一个分流问题 | 常见误判 |
|---|---|---|---|
| 游戏 | Engine/应用线程、GPU completion、CPU/GPU freq、thermal、rail、帧统计 | 引擎主动调帧，还是系统容量下降后被迫掉帧 | 只用 App Window FrameTimeline 代表 SurfaceView 游戏内容 |
| 地图 | 手势 marker、瓦片网络、定位、主线程、RenderThread、GPU、thermal | 首屏加载尖峰，还是持续交互负载 | 把网络迟到写成渲染超时 |
| 视频 | MediaCodec、SurfaceView/TextureView、BufferQueue、fence、SF/HWC、network、display rail | 解码、缓冲、合成、刷新节奏哪一段晚 | 把 `releaseOutputBuffer()` 当成屏幕已显示 |
| WebView | provider 版本、renderer、JS/layout、图片、网络、宿主 HWUI、媒体 Layer | renderer、宿主还是独立媒体层形成负载 | 只看宿主主线程和单一进程 |

案例缺少实机 trace 时，只保留复现脚本与证据缺口记录（明确标注「无实机证据」），不填写固定收益或跨设备阈值。后续补证据时应保存 trace 时间区间、线程/Layer、counter 名称、Batterystats UID 字段和对照结果。

## 现场结论模板

一条可复核的结论应包含现象、时序、约束、性能结果、能量证据和边界：

> Pixel X、Android 17 构建 Y、120 Hz、固定亮度和数据集下，连续地图手势 95 秒后 SKIN overall status 从 NONE 升到 MODERATE；同一窗口 CPU cluster policy 上限下降，渲染线程工作量保持稳定而完成时间增长，随后出现连续 App deadline miss。冷却设备并重复同脚本后，上限与帧时间恢复。ODPM 缺少 GPU rail，因此当前证据支持 thermal/CPU 容量约束参与卡顿，不支持 GPU 能量归因。

若只有“温度高、频率低、帧红”，结论应停在相关性，并列出缺少的 frequency limit、cooling state、工作量稳定性或冷却对照。

## 章节导航

| 继续排查 | 章节 |
|---|---|
| Thermal HAL、Linux thermal core、headroom | `5.5` |
| DVFS、调度与 CPU capacity | `5.4`、`5.10` |
| 场景化流畅性入口 | `7.15` |
| Perfetto power/thermal 轨道 | `13.2`、`14.11` |
| Batterystats、BatteryUsageStats 与应用功耗 | `25.1`、`25.2` |
| SurfaceView、TextureView、视频和 HWC | `18.4`、`18.6`、`18.15` |

## 源码与官方资料

- [AOSP Android 17 `ThermalManagerService`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/power/thermal/ThermalManagerService.java)
- [AOSP Android 17 `PowerManager`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/PowerManager.java)
- [AOSP Android 17 Thermal HAL AIDL](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/thermal/aidl/android/hardware/thermal/)
- [AOSP Android 17 `IPowerStats.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl)
- [Android 17 Perfetto `AndroidPowerConfig`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/protos/perfetto/config/power/android_power_config.proto)
- [Android 17 内核 thermal tracepoints](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/drivers/thermal/thermal_trace.h)
- [Android 17 内核 power tracepoints](https://android.googlesource.com/kernel/common/+/android17-6.18-2026-06_r6/include/trace/events/power.h)
- [AOSP Thermal mitigation](https://source.android.com/docs/core/power/thermal-mitigation)
- [AOSP Power Stats HAL](https://source.android.com/docs/core/power/power-stats-hal)
- [Perfetto power data sources](https://perfetto.dev/docs/data-sources/battery-counters)
- [Perfetto CPU frequency and idle](https://perfetto.dev/docs/data-sources/cpu-freq)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [PowerManager API](https://developer.android.com/reference/android/os/PowerManager)
- [Android Studio Power Profiler](https://developer.android.com/studio/profile/power-profiler)
- [Battery Historian](https://developer.android.com/topic/performance/power/battery-historian)
- [WakeLock 识别指南](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls)
- [Adaptive Refresh Rate](https://developer.android.com/develop/ui/views/animations/adaptive-refresh-rate)
