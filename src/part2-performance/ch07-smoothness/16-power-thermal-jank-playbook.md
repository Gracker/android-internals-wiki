---
title: "耗电/发热伴随卡顿排障入口"
chapter: "7.16"
status: ready-for-review
drafted_date: "2026-05-18"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-05-18"
last_verified_against: "Perfetto docs + Android Developers power docs + AOSP android-16.0.0_r1 public paths"
confidence: medium-high
tags: [jank, power, thermal, perfetto, battery-historian]
related_chapters: ["5.5", "5.10", "7.15", "11.1", "13.2", "14.11", "25.1", "25.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "章节深挖/研究素材/官方文档"
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
    path: "https://developer.android.com/topic/performance/power/battery-historian"
  - type: official
    path: "https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl"
  - type: aosp
    path: "hardware/interfaces/thermal/aidl/android/hardware/thermal/"
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
列出 Pixel / AOSP 设备、厂商设备、低端机在 power rail、thermal HAL、GPU counter、网络 counter 可见性上的差异。没有设备级证据时标注待验证，不写泛化结论。

## 扩展

### 🔸 Power rail 命名与 EnergyConsumer 对照
整理 rail / channel、EnergyConsumer、BatteryUsageStats 三套口径之间的区别，作为 11.1 与 25.1 的补充索引。

### 🔸 热状态驱动的线上降级策略
补充根据 thermal status / thermal headroom 调整动画、刷新率、网络重试和后台任务节奏的策略，但需要标注 API 版本和设备限制。

### 🔸 游戏、地图、视频、WebView 四类场景案例
每类场景给出采集配置、第一判断点和常见误判，案例材料不足时保留为待补充。

<!-- outline-end -->

## 本节定位

本节处理一类混合投诉：用户同时说“滑动卡”“手机烫”“掉电快”。这类问题不能只按流畅性分析，也不能只按功耗分析。帧时间、CPU / GPU 频率、热状态、WakeLock、后台任务和网络重试要放进同一个时间窗口里看。

前文已经分别讲过热管理、后台调度、功耗诊断和场景化卡顿排障。本节只提供分流入口和证据组织方式：先判断问题属于前台高负载、热限制、后台耗电，还是多因素叠加；再把对应章节接上。

[来源: intake/research-gaps.md#2026-05-17-7.15]

## 投诉入口拆分：掉帧、发热、掉电分别代表什么

线上反馈里的三个词对应的系统信号不同。掉帧是用户看到的呈现节奏异常，发热是设备热平衡被持续负载推高，掉电快是较长窗口内电量消耗过快。三者可能同时发生，也可能互相独立。

| 用户反馈 | 优先确认的事实 | 主要观察入口 | 常见下一步 |
|----------|----------------|--------------|------------|
| “滑动卡、动画卡” | 哪些帧超过 Expected Timeline，超时发生在 App、RenderThread、GPU 还是 SurfaceFlinger | FrameTimeline、主线程、RenderThread、SurfaceFlinger、sched | 进入 §7.3、§7.15 或 §22.x 的渲染排障 |
| “越用越烫，然后开始卡” | 温度上升后 CPU / GPU 频率上限是否下降，线程是否仍在高负载运行 | thermal status、thermal zone、CPU frequency、GPU counter、sched | 进入 §5.5 热管理与 §5.4 DVFS 判断 |
| “不操作也掉电” | 灭屏或后台窗口内是否有 WakeLock、Job、网络、定位、前台服务 | Battery Historian、`dumpsys batterystats`、`dumpsys power`、JobScheduler | 进入 §25.1、§25.2、§5.10 |
| “页面一打开又卡又耗电” | 前台渲染、网络加载、解码、WebView / 地图 / 视频是否在同一窗口叠加 | FrameTimeline、network、CPU / GPU freq、power rails | 先切分前台工作，再按 CPU / GPU / 网络拆 |

分流时不要从“卡顿根因”直接跳到代码。更稳的顺序是：先确认时间窗口，再确认用户可见帧是否异常，然后看该窗口里有没有持续高频、热限制、后台唤醒或网络脉冲。单帧慢只能解释一次卡顿，解释不了一小时掉电；一小时耗电异常也不能直接证明某一帧为什么红。

[已验证: 官方文档, perfetto.dev/docs/data-sources/frametimeline]
[已验证: 官方文档, developer.android.com/topic/performance/power/battery-historian]

## Perfetto 联合采集模板

短时前台场景用 Perfetto；长时后台耗电用 Battery Historian / `batterystats`；两者要用同一段场景脚本和同一组时间戳对齐。Perfetto 负责回答“这一分钟线程、频率、帧和 power rail 怎么重叠”，BatteryStats 负责回答“这个 UID 在更长时间里累计消耗了什么”。

下面这份配置用于抓前台卡顿伴随温升的 30-120 秒窗口。重点是 FrameTimeline、调度事件、CPU 频率、thermal 采样和 Android power 数据源。

```protobuf
buffers: {
  size_kb: 65536
  fill_policy: RING_BUFFER
}
duration_ms: 60000

# App / SurfaceFlinger 帧时间线，Android 12+ 可用。
data_sources: {
  config {
    name: "android.surfaceflinger.frametimeline"
  }
}

# 线程调度、CPU 频率、thermal 事件。
data_sources: {
  config {
    name: "linux.ftrace"
    ftrace_config {
      ftrace_events: "sched/sched_switch"
      ftrace_events: "sched/sched_wakeup"
      ftrace_events: "power/cpu_frequency"
      ftrace_events: "power/cpu_idle"
      ftrace_events: "power/suspend_resume"
      ftrace_events: "thermal/thermal_temperature"
      ftrace_events: "thermal/thermal_zone_trip"
      atrace_categories: "gfx"
      atrace_categories: "view"
      atrace_categories: "freq"
      atrace_categories: "power"
      atrace_apps: "com.example.app"
    }
  }
}

# 频率和温度轮询，弥补事件型记录在 trace 开头缺初始值的问题。
data_sources: {
  config {
    name: "linux.sys_stats"
    sys_stats_config {
      cpufreq_period_ms: 500
      thermal_period_ms: 1000
    }
  }
}

# Android 电池与 power rail；rail 读数取决于设备是否暴露 ODPM / PowerStats HAL。
data_sources: {
  config {
    name: "android.power"
    android_power_config {
      battery_poll_ms: 1000
      collect_power_rails: true
    }
  }
}

# 进程和线程名映射，方便把 tid 对回业务线程。
data_sources: {
  config {
    name: "linux.process_stats"
    process_stats_config {
      scan_all_processes_on_start: true
    }
  }
}
```

这份模板不能保证每台设备都有 rail、GPU counter 或网络包级数据。Perfetto 的 power rail counter 依赖设备厂商暴露的硬件计量能力，平台侧通过 Android `IPowerStats` HAL 读取；Perfetto 官方文档也明确 rail 的存在性和精度取决于设备厂商。缺 rail 时，用 `android.power` 的电池计数器、`dumpsys batterystats`、Power Profiler 或外接功耗仪补证据。网络包级轨道在不同内核和设备上可见性不稳定，App 侧应补业务请求 marker、`TrafficStats` tag 或代理层日志做时间对照。 [已验证: 官方文档, perfetto.dev/docs/data-sources/battery-counters] [已验证: AOSP, hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl]

CPU 频率建议同时采 `power/cpu_frequency` 和 `linux.sys_stats.cpufreq_period_ms`。Perfetto 官方说明事件型频率记录只在频率变化时出现，trace 开头可能为空；轮询能补初始快照。 [已验证: 官方文档, perfetto.dev/docs/data-sources/cpu-freq]

长时间后台场景不要用超长 Perfetto trace 硬扛。更合适的采集方式是重置 BatteryStats，执行 30 分钟到数小时的场景，再导出 bugreport。

```bash
adb shell dumpsys batterystats --reset
adb shell dumpsys batterystats --enable full-wake-history

# 断开 USB，执行固定场景：息屏播放、后台同步、弱网重试、地图导航等。
# 场景结束后重新连接设备。
adb bugreport bugreport-power.zip
adb shell dumpsys batterystats --charged > batterystats-charged.txt
adb shell dumpsys power > dumpsys-power.txt
adb shell dumpsys jobscheduler > dumpsys-jobscheduler.txt
```

`full-wake-history` 会让 WakeLock 事件更容易出现在 bugreport 中，但历史缓冲区容量有限，长时间测试要控制窗口。Battery Historian 已不再活跃维护；它仍适合离线查看旧格式 bugreport，新的短时分析优先用 System Trace、Power Profiler 或 Macrobenchmark PowerMetric。 [已验证: 官方文档, developer.android.com/topic/performance/power/battery-historian]

## CPU/GPU 持续负载与热限制判读

热限制造成的卡顿有一个典型形态：负载仍高，频率却持续下探，随后帧时间变长。普通 DVFS 降频通常发生在负载变低之后；热限制是温度把频率上限压下来，即使 top-app 线程还在忙，CPU / GPU 也拿不到之前的频点。

| Trace 形态 | 更可能的解释 | 证据要求 |
|------------|--------------|----------|
| 单帧 App Actual 超过 Expected，前后频率和温度稳定 | 代码路径或调度偶发慢 | 对齐主线程、RenderThread、sched，找锁、IO、GC、Binder 或绘制负载 |
| 多帧连续超时，CPU 频率维持高位，thermal status 无变化 | 前台持续负载超预算 | 看业务线程是否持续 Running，GPU / RenderThread 是否排队 |
| 多帧连续超时，CPU utilization 高但频率逐步下降，thermal zone 或 status 同步上升 | 热限制介入 | 看 `thermal_zone_trip`、thermal status、CPU freq 上限、FrameTimeline 同一窗口 |
| 主线程长时间 Runnable 但不 Running，频率不低 | 调度抢占或后台线程争用 | 看 top-app 线程优先级、后台线程池、Binder 线程和 CPU 迁移 |
| App 帧正常，SurfaceFlinger 或 Display frame 超时 | 合成、显示或 HWC 侧压力 | 回到 SurfaceFlinger、HWC composition type、Display/VSYNC 轨道 |

判断时把四条线放到一屏：FrameTimeline 红帧、top-app 主线程 / RenderThread / 业务线程、CPU / GPU 频率、thermal status 或 thermal zone。只要其中一条缺失，结论就要降级。例如只有“机身热 + 红帧”，只能说热场景相关；要写“热限制导致卡顿”，还要看到频率上限被压低或 thermal trip / status 变化。

GPU 侧更容易遇到设备能力缺口。部分设备不暴露稳定的 GPU frequency、GPU busy 或 GPU power rail；这种情况下可以把 RenderThread、GPU completion、SurfaceFlinger 合成和显示 rail 作为旁证，但不要写成 GPU 根因。游戏或视频场景如果使用 SurfaceView，FrameTimeline 对 App 帧的覆盖边界也要单独标注，详见 §7.3 和 §13.2。 [已验证: 官方文档, perfetto.dev/docs/data-sources/frametimeline]

## Wakelock、JobScheduler/WorkManager 与网络重试

掉电快和卡顿同现时，先分亮屏和灭屏。亮屏掉电常见于显示、GPU、CPU、网络和定位叠加；灭屏掉电更常见于 WakeLock、Job、Alarm、前台服务、定位和网络重试。Battery Historian / `batterystats` 的价值在于按 UID 统计长时间窗口，Perfetto 的价值在于追某一次唤醒或某一段前台尖峰。

| 异常信号 | BatteryStats / Historian 入口 | Perfetto 或命令补证 | 处理方向 |
|----------|-------------------------------|---------------------|----------|
| Partial WakeLock 长时间覆盖灭屏窗口 | Userspace Wakelock、`dumpsys batterystats --charged` | `dumpsys power` 看当前活跃锁 | 检查 tag、释放路径、超时、异步任务生命周期；详见 §25.3 |
| WorkManager / JobScheduler 反复执行 | Job / Sync 记录、UID CPU time | `dumpsys jobscheduler`、业务日志 | 合并 unique work、补约束、修失败重试；详见 §5.10、§25.2 |
| 弱网下掉电与发热 | network 行密集短脉冲、radio active 时间 | 请求 marker、OkHttp event、TrafficStats tag | 降低重试频率、批量请求、离线缓存；详见 §24.4、§24.5 |
| 前台服务常驻 | App 处于 foreground service，WakeLock 或 network 持续 | `dumpsys activity services`、通知与业务状态 | 校验 FGS 类型、用户可见性、停止条件；详见 §25.2 |

Android Developers 的 WakeLock 文档明确把 AlarmManager、SensorManager、WorkManager 等系统 API 和库产生的锁纳入排查范围。App 没有直接调用 `PowerManager.newWakeLock()`，也可能因为 WorkManager / JobScheduler 正在执行、定位或音频播放而被系统归因到 WakeLock。 [已验证: 官方文档, developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls]

网络重试要看“次数”和“形态”。一次 2 MB 的批量同步不一定比 100 次 20 KB 的短连接更耗电；后者会反复拉起 radio / Wi-Fi 活跃状态，还会让 CPU 在短窗口里频繁醒来。若同一段时间 FrameTimeline 也红，要先确认这些请求是否发生在 UI 交互路径上；若只在灭屏后发生，按后台功耗治理处理，不要把它混进前台渲染根因。

## 渲染负载、刷新率与显示功耗

高刷新率把帧预算缩短，也会提高显示和 GPU 的工作频率。120Hz 下每帧预算约 8.33 ms；如果页面还有复杂动画、透明叠加、视频解码、地图瓦片加载或 WebView JS 执行，CPU、GPU、Display 和网络可能在同一时间窗口拉高。排障时要把“帧是否超时”和“设备是否正在持续高功耗”分开记录，再看两者是否同窗发生。

Android 15-QPR1+ 的 Adaptive Refresh Rate 会让 Expected Timeline 随显示节奏变化。分析 FrameTimeline 时，不要套固定 16.67 ms 或 8.33 ms 阈值；以 Expected Slice 宽度为准，再结合 VSYNC / Display mode 轨道。Expected 变宽且 Actual 在窗口内完成，通常是刷新率策略变化；Expected 很窄而 Actual 溢出，才按掉帧继续追。动态刷新率规则见 §2.18，标准卡顿定位流程见 §7.3。

几个场景的第一判断点：

- 游戏：看引擎线程、RenderThread / GPU completion、Swappy 或自研帧统计、CPU / GPU freq 和 thermal status。没有 GPU counter 时，结论只写到“渲染负载相关”。
- 地图：看瓦片加载、定位、网络、主线程 marker 和 RenderThread。平移时 CPU / GPU / 网络同时升高，要区分首屏加载和持续手势。
- 视频：看解码线程、SurfaceView / TextureView 路径、显示刷新率、音频和网络缓冲。tunneled playback、Codec2 和渲染原理见 §8.8。
- WebView：看 JS、布局、图片解码、网络重试、Renderer 进程和页面驻留时长。功耗取舍见 §25.10。

这一节不重复渲染机制。要写进缺陷报告的结论应保持可复核：哪段场景、哪几帧、哪个线程、哪个频率或 power rail、哪条网络请求。缺其中一项，就把判断改成待验证。

## 设备能力差异与证据等级

功耗与热问题的证据强度高度依赖设备能力。Pixel / AOSP 参考设备通常更容易拿到 power rail、thermal HAL 和 Perfetto 轨道；厂商设备可能隐藏 rail 命名、裁剪 GPU counter，或把温控策略放在 vendor thermal engine；低端机还可能缺少稳定的 ODPM / GPU 读数。

| 证据等级 | 可用证据 | 可写结论 | 风险 |
|----------|----------|----------|------|
| A | FrameTimeline + sched + CPU/GPU freq + thermal status/trip + power rail + BatteryStats | 某窗口内负载、热限制、帧超时和能耗同窗发生 | 仍需标注设备型号、系统版本、亮度、刷新率、温度起点 |
| B | FrameTimeline + sched + CPU freq + thermal zone / status，缺 rail | 可以判断热限制或持续负载是否影响帧时间 | 不能给硬件域能耗拆分结论 |
| C | BatteryStats / Historian + 业务日志，缺 Perfetto | 可以判断长时间 WakeLock、Job、网络、定位是否异常 | 不能解释单帧卡顿 |
| D | 用户反馈 + 电量百分比，缺系统证据 | 只能作为待复现线索 | 不能写技术根因 |

对比不同设备时，必须记录设备型号、系统版本、内核版本、电量区间、亮度、刷新率、网络类型、温度起点、场景时长和后台 App 状态。同一段代码在两台设备上表现不同，可能来自散热、power profile、thermal engine、HWC 能力或刷新率策略差异，不一定是 App 代码差异。

[已验证: 官方文档, source.android.com/docs/core/power/thermal-mitigation]
[已验证: 官方文档, source.android.com/docs/core/power/power-stats-hal]

## Power rail 命名与 EnergyConsumer 对照

Power rail、EnergyConsumer 和 BatteryUsageStats 是三套口径。rail / channel 更接近硬件测量，名字通常来自厂商 PMIC 或 SoC 电源域；EnergyConsumer 是 PowerStats HAL 对外暴露的能量消费者抽象；BatteryUsageStats 是 Framework 将 CPU、网络、传感器、WakeLock 等统计换算到 UID 或组件后的估算结果。

| 口径 | 适合回答的问题 | 不适合回答的问题 |
|------|----------------|------------------|
| Power rail / channel | 某段 trace 里 CPU、display、modem 等硬件域能量是否上升 | 某个 Java 方法消耗了多少电 |
| EnergyConsumer | 设备 HAL 暴露了哪些能量消费者，是否能按类型读取 | 不同厂商 rail 名的语义对齐 |
| BatteryUsageStats / BatteryStats | 某 UID 在长窗口内 CPU、网络、WakeLock 等统计 | 短时帧级功耗、GPU 子阶段拆分 |

Perfetto 里的 rail 名不要跨设备直接比较。`S4M_VDD_CPUCL0`、`VSYS_GPU`、`display` 这类名字只能在同一设备或同一平台系列内解释；不同厂商即使名字相近，采样点和换算口径也可能不同。跨设备报告更适合写“设备 A 的 CPU cluster rail 在测试窗口上升”，不要写“所有 Android 设备的 CPU 功耗上升同样幅度”。 [已验证: 官方文档, perfetto.dev/docs/data-sources/battery-counters]

## 热状态驱动的线上降级策略

线上降级策略的目标是把负载从热墙前移走，而不是等系统把频率压下来。Android 10+ 提供 thermal status 回调，App 可以在状态升高时降低非必要负载；`getThermalHeadroom()` 可用于持续高负载场景的预判，但 API 版本、返回值稳定性和设备支持情况要按官方文档与实机验证标注。 [已验证: 官方文档, source.android.com/docs/core/power/thermal-mitigation] [待验证: 不同厂商对 thermal headroom 的返回稳定性]

可执行的降级动作按场景分：

- 动画和列表：降低动画密度、暂停非必要动效、减少预取窗口，避免在热状态升高后继续制造 RenderThread 和 GPU 压力。
- 地图和视频：降低瓦片刷新、码率、解码分辨率或 UI 覆盖层复杂度，同时记录用户可见质量变化。
- 网络重试：热状态升高时拉长退避间隔，弱网下合并请求，避免 CPU、radio 和屏幕同时持续活跃。
- 后台任务：延后普通 WorkManager / JobScheduler 任务；用户不可见任务优先等充电、网络稳定或设备冷却后执行。
- 高刷新率：业务侧能控帧率时，在温度升高后降低目标帧率；系统刷新率策略和 SurfaceFlinger 行为仍以 §2.18 为准。

降级策略必须有退出条件。thermal status 回落、用户退出高负载页面、网络恢复或任务完成后，应恢复默认策略或停止临时降级。否则一次热状态变化可能把体验长期锁在低质量档位。

## 游戏、地图、视频、WebView 四类场景案例

当前章节没有本地实机 trace，案例只给排障路径，不写固定收益数字。后续补案例时，每个场景至少要带设备型号、Android 版本、刷新率、温度起点、测试时长、采集配置、FrameTimeline 截图或 SQL、BatteryStats / rail 证据。

| 场景 | 采集配置 | 第一判断点 | 常见误判 |
|------|----------|------------|----------|
| 游戏 | FrameTimeline / Swappy stats、sched、CPU/GPU freq、thermal、power rails | 热状态升高后是否出现频率上限下降和帧时间拉长 | 把引擎主动降帧误判成系统掉帧 |
| 地图 | FrameTimeline、network、location、sched、CPU/GPU freq | 手势期间瓦片、定位、渲染是否叠加 | 只看主线程，漏掉网络重试和 GPU 绘制 |
| 视频 | 解码线程、SurfaceView / TextureView、Display rail、network、audio | 掉帧是否来自解码、合成、网络缓冲或刷新率策略 | 把缓冲卡顿写成渲染卡顿 |
| WebView | Renderer 进程、JS / layout marker、network、FrameTimeline、BatteryStats | JS、图片解码、网络和 Renderer 内存是否同窗异常 | 只按原生 / Web 二分，不看页面质量和缓存策略 |

这些案例适合与 §7.15 合并成场景手册索引。真实报告里，每个结论后面都要跟证据位置：trace 时间戳、线程名、slice 名、rail / BatteryStats 字段和业务 marker。没有证据的案例只能保留为待补充。

## 参考资料

- [Perfetto: Power data sources](https://perfetto.dev/docs/data-sources/battery-counters)
- [Perfetto: CPU frequency and idle states](https://perfetto.dev/docs/data-sources/cpu-freq)
- [Perfetto: Android Jank detection with FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [AOSP: Thermal mitigation](https://source.android.com/docs/core/power/thermal-mitigation)
- [Android Developers: Analyze power use with Battery Historian](https://developer.android.com/topic/performance/power/battery-historian)
- [Android Developers: Identify and optimize wake lock use cases](https://developer.android.com/develop/background-work/background-tasks/awake/wakelock/identify-wls)
