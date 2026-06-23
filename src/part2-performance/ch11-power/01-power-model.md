---
title: "Android 功耗模型"
chapter: "11.1"
section: "11.1"
status: "finalized"
pipeline_stage: "ready-to-publish"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
tags: [['power', 'battery', 'power_profile', 'BatteryStats', 'ODPM', 'Coulomb Counter', 'Fuel Gauge', 'IPowerStats', '功耗归属']]
confidence: medium
last_verified: "2026-06-20"
last_verified_against: "AOSP android-17.0.0_r1 + PowerAttributor / MultiStatePowerAttributor / PowerStatsProcessor 归因管线"
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-06-20"
reviewed_by: "openclaw-task6"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
task9_result: "pass-tech-review"
path: "https://developer.android.com/topic/performance/power"
note: "Android 17+ 屏幕功耗归因处理器"
related_chapters: "[\"5.4\", \"5.5\", \"5.6\", \"11.2\", \"11.3\", \"13.1\"]"
task2b_result: "fixed"
task2b_state: "fixed"
last_task2b_at: "2026-06-20T00:50:00+08:00"
last_task2b_lite_at: "2026-05-27"
repaired_date: "2026-06-20"
repaired_by: "openclaw-task2b"
task9_reviewed_date: "2026-06-20"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-20T03:27:28+08:00"
last_task6_audit: "2026-06-20"
last_task9_audit: "2026-06-20"
last_task9_autofix_at: "2026-06-20"
task6_result: "pass-light-edit"
task6_state: "reviewed"
task6_reviewed_date: "2026-06-20"
task6_reviewed_by: "openclaw-task6"
last_task6_at: "2026-06-20T03:08:00+08:00"
review_type: "task6-writing-quality-review"
task9_state: "reviewed"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-20
---

# Android 功耗模型

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 功耗模型：power_profile.xml 定义各硬件模块的功耗参数
- 🔹 功耗组成：CPU、Display、GPU、Cellular、WiFi、GPS、Audio、Camera
- 🔹 BatteryStats 的工作原理与数据采集
- 🔹 Coulomb Counter / Fuel Gauge 与功耗估算的区别
- 🔹 App 耗电量的归属算法

### 扩展（可选深入）

- 🔸 ODPM（On-Device Power Monitor）与 Pixel 设备的硬件功耗监测
- 🔸 功耗模型的准确性问题与校准方法

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 Android 功耗模型

当用户抱怨某个 App 太耗电时，开发者往往很难直接回答原因。App 本身没有显式的"耗电接口"，耗电也不是单个进程自己就能决定的事。Android 会把电池消耗拆到各个硬件模块，再按使用时间和资源占用归属到不同 App。不了解这套模型，我们就很难判断"设置 → 电池 → 电池使用情况"里的百分比是怎么来的，也很难判断该从哪里优化。

理解功耗模型之后，我们能判断哪些功耗数据可用，以及这些数据有多可信。当我们打开 Battery Historian 看到一个 App 的 CPU 耗电占比异常时，我们需要知道这个数字是来自硬件实测还是软件估算，误差范围有多大，哪些场景下数据可信、哪些场景下需要额外验证。

我们在前几章已经讨论了 CPU 调度（§5.1）、DVFS（§5.4）、热管理（§5.5）和 Android 功耗管理机制（§5.6）。那些章节讲的是系统如何"省电"，本章讨论的是系统怎么判断谁"费了电"，以及这个判断有多准确。

## 功耗模型的基础：power_profile.xml

Android 功耗模型的核心是一个叫 `power_profile.xml` 的 XML 文件。它位于 AOSP 的 `frameworks/base/core/res/res/xml/power_profile.xml`，定义了设备上每个硬件模块在各种工作状态下的电流消耗值（单位 mA）。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/res/res/xml/power_profile.xml]

`power_profile.xml` 的作用是给回退估算提供参数：当系统无法从硬件直接获取实际功耗数据时，就用文件里的预设值来估算。系统记录某个硬件模块工作了多长时间，再乘以这个模块在对应状态下的电流值，得到估算电量。

[已验证: 官方文档, source.android.com/docs/core/power]

### power_profile.xml 的结构

文件的根元素是 `<device name="Android">`，内部通过 `<item>` 和 `<array>` 两种标签定义功耗参数。Android 16 公共示例里更常见的是带 `display` 和 `cluster` 后缀的现代命名，例如 `screen.on.display0`、`screen.full.display0`、`cpu.speeds.cluster0`。下面放一个简化过的现代结构示意，数值只用于说明字段形态，不代表真实设备参数：

```xml
<device name="Android">
    <!-- Display 0：亮屏基础电流，单位 mA -->
    <item name="screen.on.display0">83</item>
    <!-- Display 0：满亮度附加电流，单位 mA -->
    <item name="screen.full.display0">260</item>

    <!-- CPU cluster0：频点表 -->
    <array name="cpu.speeds.cluster0">
        <value>300000</value>
        <value>600000</value>
        <value>800000</value>
        <value>1200000</value>
        <value>1500000</value>
    </array>
    <array name="cpu.active.cluster0">
        <value>52</value>
        <value>78</value>
        <value>105</value>
        <value>145</value>
        <value>210</value>
    </array>

    <!-- CPU 公共基础项：Android 16 公共 profile 中为 array 形态 -->
    <array name="cpu.active">
        <value>52</value>
    </array>
    <item name="cpu.idle">3.5</item>

    <item name="wifi.on">3</item>
    <item name="wifi.scan">70</item>
    <item name="wifi.active">120</item>

    <item name="radio.active">180</item>
    <item name="radio.scanning">65</item>
    <array name="radio.on">
        <value>3</value>
        <value>5</value>
        <value>8</value>
    </array>

    <item name="gps.on">50</item>
    <item name="bluetooth.active">20</item>
    <item name="bluetooth.on">1</item>
    <item name="camera.avg">550</item>
    <item name="audio">60</item>
    <item name="video">50</item>
</device>
```

[待验证: 以上数值为示意性占位，字段名按 Android 16 公共 profile 的现代命名整理。OEM 文件可能继续扩展 display / cluster 项，AOSP 默认文件中的数值也可能仍是占位值]

这个结构中有几个关键细节。

CPU 功耗拆为“基础项 + 各 cluster 频点项”两层，因为现代 SoC 的 CPU 功耗随频率非线性增长——1.5GHz 时的电流可能是 300MHz 时的数倍。异构 CPU 的 profile 文件中常见 `cpu.speeds.cluster0`、`cpu.active.cluster0`、`cpu.speeds.cluster1` 这类独立数组，各自描述一个 cluster。旧资料中也有不带后缀的 legacy 名称，但对照 Android 16 公共文件时，优先看带 `display` / `cluster` 后缀的写法。

蜂窝网络 Radio 的功耗按信号强度分档。信号弱时 Radio 需要更大发射功率来维持连接，电流消耗可能比信号强时高出两三倍。这就是在地铁里刷手机特别费电的原因之一。

AOSP 默认 `power_profile.xml` 中的值都是占位值（通常是 0.1mA）。OEM 必须在出货前用实测硬件数据替换这些占位。如果厂商跳过这一步，后续所有功耗归属结果都会产生系统性偏差。

## 功耗组成

了解了 power_profile.xml 的结构之后，我们再拆开看 Android 设备的主要功耗组成。只有先看清这些模块，我们才能理解为什么有些 App 看起来什么都没做却很费电，而有些 App 明明很忙却不怎么耗电。

### CPU：功耗敏感项

CPU 仍然是功耗统计里最敏感的一项，但 Android 16 的模型已经不是一句“频率时间 × 电流”能讲清的。`CpuPowerCalculator` 在 power-profile 模式下把 CPU 功耗拆成三层：`PowerProfile.POWER_CPU_ACTIVE` 表示 CPU 进入 active 状态后的基础电量；`getAveragePowerForCpuScalingPolicy()` 表示某个 scaling policy 被点亮时的附加电量；`getAveragePowerForCpuScalingStep()` 表示具体频点带来的增量。对应的时间来源也分成 `getCpuActiveTime()`、policy running time 和 `getCpuFreqTimes()`。很多设备上 scaling policy 和 cluster 接近，但 Android 16 的源码口径已经按 policy 组织。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/CpuPowerCalculator.java]

如果设备接了 `EnergyConsumer` 硬件计量，`CpuPowerCalculator` 会优先读取 `u.getCpuEnergyConsumptionUC()`，直接走 `POWER_MODEL_ENERGY_CONSUMPTION`。只有没有硬件能量数据时，才回退到 power-profile 估算。设置页里的 CPU 百分比也是沿着这套归属流程产出的，不能一概当成 `power_profile.xml` 查表结果。

在 CPU cluster 能量可用的设备上，当 HAL 上报 `EnergyConsumerType.CPU_CLUSTER` 类型的 `EnergyConsumer` 时，Framework 可消费其硬件能量读数，再结合 UID 的 CPU time、policy running time 和 freq step 统计做归属。`EnergyConsumer` 是包含 `type` 字段的 parcelable，类型枚举定义在 `EnergyConsumerType.aidl`（如 `CPU_CLUSTER`、`DISPLAY`、`WIFI` 等），不是 `EnergyConsumer` 自身持有的 TYPE 常量。[已验证: AOSP android-16.0.0_r1, hardware/interfaces/power/stats/aidl/android/hardware/power/stats/EnergyConsumerType.aidl]

这里的优先顺序是 measured energy 先行，`power_profile.xml` 的 mA 均值只做兜底；读设置页 CPU 耗电时，不要把它理解成单纯的运行时长乘电流。

组件是否走 measured energy path，取决于 HAL 能力和统计支持。CPU、Screen 这类组件在支持的设备上更容易拿到硬件能量数据；WiFi、Radio、蓝牙等组件则要看 HAL 是否提供对应的 measured energy 或 controller activity 统计。`BatteryUsageStats` 会优先使用硬件能量数据，缺失时才回退到 power-profile 或 controller-based 估算。

把这套模型写成近似公式，会更接近源码：

```text
CPU charge ≈ cpu.active × activeTime
          + Σ(policyPower × policyRunningTime)
          + Σ(freqStepPower × freqStepTime)
```

这里用 charge 而不是 mWh，是因为 `power_profile.xml` 里没有 `cpu.voltage` 数组，当前 AOSP 也不是靠一个电压表把 CPU 时间直接换成能量。HAL 侧如果提供实测值，常见原始单位是 uWs；Framework 在 `BatteryStatsImpl` 和 `BatteryConsumer` 侧再转换成 uC、mAh 等更适合归属和展示的单位。把 HAL 原始单位、Framework 内部统计单位、设置页展示单位混在一层，公式就容易写错。

上面是 Android 16 及更早版本的 CPU 功耗三层模型。到 Android 17，归因管线做了重构：

> **Android 17 归因管线变更**：android-17.0.0_r1 的 `frameworks/base/services/core/java/com/android/server/power/stats/` 目录已不再包含 `CpuPowerCalculator.java`。CPU 功耗归因改为由 `PowerAttributor` 接口承接；默认实现 `processor/MultiStatePowerAttributor` 通过 `AggregatedPowerStatsConfig` 配置 `processor/CpuPowerStatsProcessor`。`CpuPowerStatsProcessor` 内部仍然消费 UID 的 CPU active time、policy running time、freq step time 和可选的硬件能量数据，归因逻辑与 Android 16 的 `CpuPowerCalculator` 接近。Android 16 是过渡态：`BatteryUsageStatsProvider` 保留 `*PowerCalculator` 回退，同时已经会调用 `mPowerAttributor.estimatePowerConsumption()` 处理受支持组件。Android 17+ 读者应追踪 `PowerAttributor` → `MultiStatePowerAttributor` → `CpuPowerStatsProcessor` 路径。[已验证: AOSP android-16.0.0_r1 / android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java; frameworks/base/services/core/java/com/android/server/power/stats/PowerAttributor.java; frameworks/base/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java; frameworks/base/services/core/java/com/android/server/power/stats/processor/CpuPowerStatsProcessor.java]
这套三层模型解释了一个常见现象：两个进程的 CPU 总时长接近，耗电量仍然可能差很多。差异不只来自“跑了多久”——还取决于跑在哪个 scaling policy / cluster、跑在哪些频点、是否拿到了硬件能量数据。

### Display：最直观的耗电源

屏幕依然是大头，但“屏幕功耗不归属到 App”只覆盖了旧 batterystats 视角。`ScreenPowerCalculator` 先看 `batteryStats.getScreenOnEnergyConsumptionUC()` 是否可用。如果设备有屏幕 `EnergyConsumer` 数据，就能直接给每个 `UidBatteryConsumer` 写入 `POWER_COMPONENT_SCREEN`。如果没有，Framework 才回退到 `POWER_GROUP_DISPLAY_SCREEN_ON` 和 `POWER_GROUP_DISPLAY_SCREEN_FULL` 这套 power-profile 估算，再按前台 activity 时间把总屏幕耗电分摊到各个 UID。源码里的 `smearScreenBatteryDrain()` 还要求总前台活动时间至少 10 分钟才开始分摊。[已验证: AOSP android-16.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/ScreenPowerCalculator.java]

上述分摊逻辑是 Android 16 及更早版本的行为。Android 17 在此基础上做了简化：

> **Android 17 边界**：android-17.0.0_r1 的 `power/stats/` 目录已不再包含 `ScreenPowerCalculator.java`，屏幕功耗归因由 `processor/ScreenPowerStatsProcessor` 接管。`ScreenPowerStatsProcessor` 仍然优先读取屏幕 `EnergyConsumer`，缺失时再用 `POWER_GROUP_DISPLAY_SCREEN_ON` / `POWER_GROUP_DISPLAY_SCREEN_FULL` 估算；分摊阶段按 UID top activity duration 占比分配屏幕功耗。这里已经没有 Android 16 `ScreenPowerCalculator.smearScreenBatteryDrain()` 的 `MIN_ACTIVE_TIME_FOR_SMEARING = 10min` 门槛，只在总 top activity duration 为 0 时跳过 UID 分摊。[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/processor/ScreenPowerStatsProcessor.java]

所以，旧 batterystats 视角里常见的“屏幕是系统项”只说对了一半。到了 `BatteryUsageStats` 这层，屏幕既可能以 smear 的方式分摊到前台 UID，也可能在有硬件计量时直接带着 UID 归属结果出现。我们看设置页、电池 bugreport 和 Power Profiler 时，要先分清设备走的是哪条路径。

### GPU：隐藏的耗电源

AOSP 标准 `power_profile.xml` 和 `BatteryUsageStats` / `BatteryConsumer` 体系没有独立的 GPU power component。`PowerProfile.java` 没有 `POWER_GPU` / `gpu.active` 标准键，`android.os.BatteryConsumer` 的 `POWER_COMPONENT_*` 枚举也没有 GPU。`PowerStats` AIDL 的 `EnergyConsumerType` 枚举里同样没有 GPU 专有类型。

Framework 层的功耗归属链不会把 GPU 拆出来单独统计。GPU 功耗通常需要通过以下间接路径分析：

- 厂商 vendor rail / Channel：在 Perfetto power rails 视图中找 GPU 相关的电源轨（如 `GPU-VDD`），读取微焦耳累加值
- GPU 频率 + 利用率 × 场景归因：结合 `gpu_frequency` / `gpu_busy` counter 与当前前台 App 推算
- `dumpsys gfxinfo` 帧耗时与 GPU time 占比，间接判断 GPU 负载是否为功耗瓶颈

做游戏或视频播放类 App 的功耗分析时，GPU 是不可忽略的隐藏变量，但分析手段要跳出 `power_profile` / BatteryStats 的框架。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/res/res/xml/power_profile.xml / PowerProfile.java / BatteryConsumer.java]

### Cellular / WiFi / GPS：通信模块

通信模块的功耗有一个共同特点：它们的状态切换本身就很费电。以蜂窝网络为例：

- **连接态（radio.active）**：正在传输数据，电流最高（100-300mA）。
- **空闲态（radio.on）**：维持连接但不传输，电流较低但持续存在（3-10mA，信号弱时更高）。
- **休眠态**：完全关闭，几乎不耗电。

Radio 从休眠态切到连接态需要几百毫秒到几秒不等，期间消耗的电量也算在 Radio 活跃时间里。Android 通过一个"Radio Active Timeout"机制来管理这个问题——数据传输结束后，Radio 不会立即进入休眠，而是等待一个超时时间（通常 5 秒），如果在超时时间内有新数据需要传输，就复用已有连接，避免频繁的状态切换开销。

[已验证: 官方文档, source.android.com/docs/core/power/networks]

WiFi 和 GPS 的模式类似，但 WiFi 的活跃态功耗（约 100-150mA）通常低于蜂窝网络，GPS 的活跃态功耗约 50mA 但持续运行时的累计效果很可观。

### Audio / Camera / Bluetooth：按使用时长估算

Audio、Camera 和 Bluetooth 的功耗模型比较简单——基本上就是"开启时间 × 对应电流"。Camera 是其中的耗电大户（300-600mA），所以持续调用 Camera 的 App（如视频通话、AR 应用）在电池统计中通常排名靠前。Bluetooth LE（低功耗蓝牙）的活跃态电流只有几 mA，远低于经典蓝牙，这也是为什么穿戴设备都使用 BLE 通信。

## BatteryStats：数据采集与统计引擎

了解了功耗参数之后，我们来看 Android 是如何采集和统计这些数据的。BatteryStats 是 Android Framework 中的核心功耗统计服务，它持续运行在后台，记录每个硬件模块的状态变化和每个 App 的资源使用情况。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/BatteryStats.java]

### 采集方式：Push + Pull 混合

BatteryStats 的数据采集采用两种机制：

**Push 机制**：当硬件模块的状态发生变化时，对应的服务主动通知 BatteryStats。比如 WiFi 开启时，WiFiService 会调用 `BatteryStats.noteWifiOn()`；GPS 开始定位时，LocationManagerService 会调用 `BatteryStats.noteGpsOn()`。这种方式实时性好，不会遗漏状态变化。

**Pull 机制**：对于 CPU 使用时间这类需要持续统计的数据，BatteryStats 会定期从 `/proc/` 文件系统或内核接口拉取数据。每个进程的 CPU 时间、各频率点的运行时长都通过这种方式获取。

### 数据存储与持久化

BatteryStats 的数据以二进制格式存储在 `/data/system/batterystats.bin` 文件中。自动 reset 不是每次充满或每次拔掉充电器都会发生。`shouldResetOnUnplugLocked()` 只在几类条件下触发 reset：设备处于满电或高电量区间、从很低电量充到较高电量的显著充电，或者统计 session 因反复部分充放电拖得过长。没有满足这些条件时，拔掉充电器只会继续沿用当前统计窗口，不会重置计数器。[已验证: AOSP android-16.0.0_r1 / android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java]

Android 16 中高电量阈值硬编码为 `>= 90`；Android 17 改为 `BatteryStatsConfig.getHighBatteryLevelAfterCharge()` 配置化，默认值仍为 90，但 OEM 可通过 `BatteryStatsConfig` 覆盖。[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsConfig.java]

Battery Historian 常说的“先 reset 再采集”，指的是手动执行 `adb shell dumpsys batterystats --reset` 来切出一个干净窗口。这和系统在 unplug 时按条件自动 reset，是两套不同机制。

### dumpsys batterystats：查看原始数据

通过 `adb shell dumpsys batterystats` 命令可以查看 BatteryStats 采集到的原始数据。输出内容非常详细，包括：

- 每个 UID（对应 App）的 CPU 使用时间、各频率运行时间
- WiFi/蓝牙/Radio 的活跃时间
- WakeLock 持有时间
- Sensor 使用时间
- 网络数据包收发量
- 进程级别的前台/后台时间

这些原始数据正是 Battery Historian 可视化的数据来源。我们在 §13.1 中会详细讨论 Perfetto 的功耗分析能力，这里需要知道的是：BatteryStats 的数据是 Battery Historian 的基石，而 BatteryStats 的准确性又取决于 power_profile.xml 的参数质量和硬件监测能力。

## Coulomb Counter 与软件估算：两条路的交汇

到目前为止我们讨论的都是"软件估算"——用预设的功耗参数乘以使用时间来推算耗电量。但 Android 设备中还有一条更直接的功耗测量路径：硬件级的 Coulomb Counter。

### Coulomb Counter（库仑计）

Coulomb Counter 是一个集成在设备主板上的专用芯片，通常位于 Fuel Gauge IC 中（如 Maxim MAX17050、TI BQ 系列）。它通过直接测量流入和流出电池的电流来计算电量变化。对电流进行时间积分，就得到了电荷量（mAh）。

这种方式的精度远高于软件估算，通常可以达到 ±2-5% 的误差范围。它不受 power_profile 参数不准确的影响，也不需要对硬件模块进行抽象建模；数据来自电池侧电流积分。

[待验证: 不同设备使用的 Fuel Gauge IC 型号和精度有差异，具体数值需参考各设备数据手册]

### Fuel Gauge（电量计）

Fuel Gauge 建立在 Coulomb Counter 之上。它在电流积分之外，还会结合电池电压、温度、放电曲线等信息，综合计算出电池的 State of Charge（SoC，即电池剩余百分比）和 State of Health（SoH，即电池健康度）。

现代 Fuel Gauge IC（如 TI 的 Impedance Track 系列）采用混合算法：用 Coulomb Counter 做实时的充放电跟踪，用开路电压（OCV）在电池静置时做校准，用温度传感器做补偿。三者结合，能在动态负载下保持较高的 SoC 精度。

### 软件估算 vs 硬件测量：各自的局限

这两条路径互补，各自解决不同问题：

**软件估算的优势**是粒度细——它可以明确展示"App A 的 CPU 耗电 50mAh，WiFi 耗电 20mAh"。这种按 App、按模块拆分的能力是硬件测量做不到的，因为 Coulomb Counter 只能量到电池总出口的电流，无法区分这个电流是被谁消耗的。

**硬件测量的优势**是精度高——它可以准确展示"过去 1 小时电池总共消耗了 200mAh"。这个全局精度是软件估算难以保证的，特别是当 power_profile 参数不准时。

在实际的 Android 系统中，两者结合使用：Fuel Gauge 提供全局的电量消耗基准（电池百分比），BatteryStats + power_profile 提供按 App 的拆分归属。Android 10 引入的 IPowerStats HAL，目的之一就是弥合这两条路径之间的精度差距。

## App 耗电量的归属算法

这是功耗模型里最直接的问题：系统怎么判断某个 App 耗了 X% 的电？

### 归属的基本思路

`BatteryStatsImpl` 先记账，再由 `BatteryUsageStatsProvider` 产出归属结果。Android 15 及以下主要由各个 `*PowerCalculator` 计算；Android 16 是过渡态，`BatteryUsageStatsProvider` 保留 `*PowerCalculator` 回退，同时会调用 `mPowerAttributor.estimatePowerConsumption()`；Android 17 移除顶层 `*PowerCalculator`，归因结果由 `PowerAttributor` / `processor/*PowerStatsProcessor` 写进 `BatteryUsageStats.Builder`，再产出 `BatteryUsageStats` 和 `UidBatteryConsumer` 快照。Settings 电池页、`adb bugreport` 里的电池摘要，消费的就是这层数据；它们看的是归属后的结果，不是 HAL 原始读数。[已验证: AOSP android-15.0.0_r1 / android-16.0.0_r1 / android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java; frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java; frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java]

对不同模块，归属方式并不一样。

**CPU**：在 `CpuPowerCalculator` 路径中，如果 UID 已有 `getCpuEnergyConsumptionUC()`，计算器直接使用硬件能量数据；没有时才按 active、cluster、freq step 三层模型估算。Android 17 的 `CpuPowerStatsProcessor` 仍沿用硬件能量优先、缺失后按统计时长和 power-profile 估算的口径。

**WiFi / 蓝牙 / Radio**：按 UID 的网络活动、扫描、连接时长和流量做归属。多个 App 并发时通常需要分摊。

**GPS / Sensor**：按注册者和活跃时间归属。谁持有请求，对应时段的成本就归到谁名下。

**WakeLock**：按持有者归属。它会增加 CPU 忙碌时间，也会把本来可以进入休眠的时间变成可计费的耗电窗口。

**Screen**：可能是 smear，也可能直接按 UID 归属，取决于设备有没有屏幕 `EnergyConsumer` 数据。

### 现代功耗归属流程

我们在排查“设置页百分比”“Battery Historian 统计”和“Perfetto 看到的 rail 数据”为什么对不上时，先把三层对象分开：

- `BatteryStatsImpl` 记录的是原始时长、计数器、能量桶。
- **Android 5-15**：`BatteryUsageStatsProvider` 调用各个 `*PowerCalculator`（`CpuPowerCalculator`、`ScreenPowerCalculator`、`WifiPowerCalculator` 等）把原始数据折成组件耗电和 UID 耗电。
- **Android 16**：`BatteryUsageStatsProvider` 同时具备两条路径：不受 `PowerAttributor` 支持的组件继续走 `*PowerCalculator`，受支持组件再由 `mPowerAttributor.estimatePowerConsumption()` 写入归因结果。
- **Android 17+**：`BatteryUsageStatsProvider` 移除 `*PowerCalculator` 回退，委托 `PowerAttributor`；默认实现 `MultiStatePowerAttributor` 按组件类型配置对应的 `processor/*PowerStatsProcessor`（`CpuPowerStatsProcessor`、`ScreenPowerStatsProcessor`、`WifiPowerStatsProcessor` 等），归因结果写入 `BatteryUsageStats.Builder`。[已验证: AOSP android-16.0.0_r1 / android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/power/stats/PowerAttributor.java; frameworks/base/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java; frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java]
- `BatteryUsageStats` 和 `UidBatteryConsumer` 是 Framework 对外给 Settings、bugreport、系统服务用的归属结果。

Perfetto Power rails 和 Android Studio Power Profiler 更靠近硬件计量层；Settings 电池页更靠近 Framework 归属层。两边能互相校对，但不需要逐列完全相等，因为一个看的是 meter 或 rail，另一个看的是归属后的 consumer 或 UID。

### 计算示例

以下示例按 power-profile 回退路径演示归属逻辑，不代表带硬件计量的设备最终结果。

假设某台没有 CPU `EnergyConsumer` 数据的设备，在 5 分钟窗口内记录到：

- CPU active 30 秒，其中某个大核 scaling policy 运行 12 秒，1.2GHz scaling step 占 18 秒
- WiFi 活跃传输 60 秒
- GPS 定位 120 秒

Framework 会将 CPU 的 active 基础功耗、policy 附加功耗和 freq step 附加功耗分别累加，再与 WiFi、GPS 的组件结果合并。落到设置页时，数值还会受共享资源分摊、UID 前后台状态、是否拿到硬件能量数据的影响。本例的核心结论是：现代 CPU 归属不是单独取一段“1.2GHz × 30 秒”就完成的。

### 归属的精度问题

归属算法最大的不确定性来自两个地方。

第一，共享资源分摊。当 App A 和 App B 同时使用 WiFi 时，WiFi 模块只开启一次，但两个 UID 都会分到一部分成本。这个分摊结果适合做定位，不适合拿来当实验室级仪表。

第二，间接功耗。App 发起一次网络请求，后面可能连着内核网络栈、Radio 状态切换、DMA、内存带宽变化。Framework 能归到发起者的一部分，但不会把所有底层副作用都精确切干净。

## ODPM：从估算到实测的跨越

Android 10 把 PowerStats 放进独立 HAL 之后，功耗分析开始同时依赖两类数据：一类是 `BatteryStatsImpl` 里按 UID 记的统计账，一类是来自硬件计量器的实测能量。读源码、看 Perfetto、对照设置页时，最容易混掉的就是这两层。

### ODPM 的工作原理

ODPM 利用 PMIC 上的电量计或 vendor power meter，从硬件侧读取模块或 rail 的累积能量。它看到的是“某条供电通道从开机到现在消耗了多少能量”，不是“某个 App 精确消耗了多少电”。所以它更接近模块级计量层，不是 Settings 那种 App 归属层。

### IPowerStats HAL：HIDL 和 AIDL 是两套接口族

Android 10 和 Android 11 常见的是 HIDL `android.hardware.power.stats@1.0::IPowerStats`。这套接口的对象是 rail：

- `getRailInfo()` 返回 `RailInfo`
- `getEnergyData()` 返回 `EnergyData`
- `EnergyData.energy` 的单位是 microwatt-seconds，也就是 uWs

到了 Android 12+，AOSP 在 `power/stats/aidl` 下加入 AIDL `android.hardware.power.stats.IPowerStats`。这时要分成两组 API 看：

- `getEnergyConsumerInfo()` 和 `getEnergyConsumed()` 面向 `EnergyConsumer`，结果是 `EnergyConsumerResult.energyUWs`，可选带 `attribution[]` 按 UID 归属
- `getEnergyMeterInfo()` 和 `readEnergyMeter()` 面向 `Channel` / `EnergyMeasurement`，看的是 meter 读数，`EnergyMeasurement.energyUWs` 也是 uWs

容易混淆的关键点：AIDL 不再用 HIDL 的 `getRailInfo()` 和 `getEnergyData()` 命名；HAL 原始返回单位是 uWs，不是 mAh——mAh 通常是 Framework 或工具为了展示再换算出来的值。Framework 拿到 `EnergyConsumerResult` 时可以直接把 measured energy 合进 `BatteryUsageStats`，只有缺失这些读数时 `power_profile.xml` 才继续兜底。[已验证: AOSP android-10.0.0_r1, hardware/interfaces/power/stats/1.0/IPowerStats.hal; AOSP android-16.0.0_r1, hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl; EnergyConsumerResult.aidl; EnergyMeasurement.aidl]

### EnergyConsumer 和 rail / Channel 的区别

`EnergyConsumer` 是 Framework 关心的逻辑耗电对象，例如 CPU、Display、WiFi、GNSS 这类组件；`Rail` / `Channel` 更接近硬件计量点，名字和分组完全可以是 vendor 私有实现。Perfetto power rails、Power Profiler 常直接展示 rail / channel 视角；Settings 电池页看的是 `BatteryUsageStats` 里的 consumer / UID 视角。两边能互相校对，但不是同一张表。

### Pixel 设备的实际应用

ODPM 目前在 Google Pixel 6 及后续 Pixel 设备上完整可用。在 Pixel 6（Tensor 芯片）上，ODPM 可以监测数十个电源轨，涵盖：

- CPU 各集群（big/mid/little）的独立功耗
- GPU 功耗
- DDR/RAM 功耗
- 屏幕功耗
- Camera 传感器功耗
- 蜂窝 Modem 功耗
- WiFi/BT 模块功耗

Android Studio 从 Hedgehog 版本开始，在 Power Profiler 中集成了 ODPM 数据的可视化。开发者可以通过 System Trace 同时查看 App 行为和各硬件模块的实时功耗，这在之前只能靠外接功耗仪才能做到。

[已验证: 官方文档, developer.android.com/topic/performance/power]

### ODPM 的局限

ODPM 目前也有几个比较明确的局限：

第一，**设备覆盖有限**。ODPM 需要硬件支持（PMIC 上有功耗计数器），不是所有设备都具备这个能力。目前只有 Pixel 6+ 系列有完整支持，其他 OEM 厂商的实现参差不齐。

第二，**粒度仍然是模块级**。ODPM 可以展示某个 CPU cluster、display rail 或 modem channel 累积消耗了多少 uWs，工具界面也可能再换算成 mAh，但它无法直接回答某个 App 在这个模块上消耗了多少电。App 级归属仍然依赖 BatteryStats 的软件算法，ODPM 只是提供了一个更准确的校准基准。

第三，**采样间隔有限**。IPowerStats HAL 的轮询间隔通常在秒级，无法捕捉毫秒级的功耗毛刺。对于分析瞬间功耗峰值（如 Camera 启动时的功耗飙升），还是需要外接功耗仪。

## 功耗模型的准确性问题与校准

梳理完整个功耗模型的架构之后，需要正视一个现实：Android 的功耗估算并不总是准确的。它的准确性取决于一长串前提条件。

### 影响准确性的因素

**power_profile.xml 的参数质量**是最关键的因素。如果 OEM 厂商没有认真测量就填了近似值（或者直接用了参考设计的值），那么基于这些参数的所有估算都会有系统性偏差。一个常见的例子是：厂商测量 CPU 功耗时使用的是工程样机，而量产机更换了不同批次的 SoC（System on Chip，即手机主芯片），实际功耗可能偏差 10-20%。

**温度和老化**是另外两个被忽略的因素。电池的内阻会随温度变化（低温时内阻增大，可用容量下降），也会随充放电循环次数增加而增大。power_profile.xml 中的参数是在特定测试条件下的快照，没有考虑这些动态因素。

**模块间的耦合**也被简化处理了。当 CPU 和 GPU 同时满负载运行时，由于供电网络的共享和散热瓶颈，实际功耗不是简单叠加的。电压跌落、热节流等因素会导致实际功耗高于估算值。

### 校准方法

对于需要高精度功耗数据的应用场景（如竞品对比测试、OTA 前后的功耗回归检测），推荐采用以下校准方法：

1. **硬件功耗仪校准**：使用 Monsoon Power Monitor 或类似的外接功耗仪，测量特定场景下（如播放视频 10 分钟）的实际总耗电量，与 BatteryStats 估算值对比，计算校准系数。

2. **ODPM 数据参考**：在支持的设备上，将 ODPM 的实测数据与 power_profile 估算值对比，识别偏差最大的模块。

3. **多设备交叉验证**：不同设备上的相同 App、相同场景，如果耗电百分比差异过大，很可能其中某台设备的 power_profile 参数不准确。

## 在 Perfetto / 工具中的表现

功耗模型的数据在多个工具中都有对应的表现形式：

**Battery Historian**：这是常用的功耗分析工具。通过解析 bugreport 中的 BatteryStats 数据，Battery Historian 提供了从系统级到 App 级的功耗时间线可视化。工具能呈现屏幕亮度变化、网络状态切换、WakeLock 持有、App 前后台切换等事件与电量下降之间的对应关系。[待补充: Battery Historian 截图示例]

**dumpsys batterystats**：命令行工具，输出 BatteryStats 的原始统计数据。适合脚本化分析和自动化测试场景。常用命令组合：

```bash
# 手动重置统计（切出新的采集窗口）
adb shell dumpsys batterystats --reset

# 导出完整统计
adb shell dumpsys batterystats > batterystats.txt
```

**Perfetto + ODPM**：在支持 ODPM 的设备上，Perfetto 通过 `android.power` 数据源采集电源轨功耗数据，与 CPU 调度、线程活动等 Trace 信息同步展示。这是目前最精确的功耗分析手段。

```bash
# Perfetto 配置示例：采集 ODPM 数据
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/trace \
<<EOF
buffers: {
    size_kb: 63488
}
data_sources: {
    config {
        name: "android.power"
        android_power_config {
            collect_power_rails: true
        }
        target_buffer: 0
    }
}
duration_ms: 60000
EOF
```

Perfetto 的 Android power probe 注册的数据源名是 `android.power`；`android.hardware.power.stats` 是 HAL 接口名，不是 Perfetto 配置里的 data source。power rail 数据通过 `android_power_config` 的 `collect_power_rails` 字段启用；按需还可以开启 `battery_poll_ms`、energy breakdown、entity residency 等子项。[已验证: AOSP android-16.0.0_r1, external/perfetto/src/traced/probes/power/android_power_data_source.cc]

**Android Studio Power Profiler**：从 Hedgehog 版本开始集成，在 System Trace 视图中直接显示 ODPM 电源轨数据，与 CPU、线程、Frame 时间线同步展示。适合 App 开发者做日常功耗分析。

**PowerMonitor API（Android 15+）**：Android 15 引入了公开的 `android.os.PowerMonitor`、`android.os.PowerMonitorReadings` 与 `android.os.health.SystemHealthManager`，允许 App 在运行时程序化查询实时能量消耗。这套 API 不依赖 bugreport 或离线分析，适合构建线上功耗自审计能力。

入口路径：`context.getSystemService(Context.SYSTEM_HEALTH_SERVICE)` 获取 `SystemHealthManager`，然后调用 `getSupportedPowerMonitors(executor, Consumer<List<PowerMonitor>>)` 查询设备支持哪些 monitor，再按需调用 `getPowerMonitorReadings(List<PowerMonitor>, Executor, OutcomeReceiver<PowerMonitorReadings, RuntimeException>)` 读取能量快照。`PowerMonitorReadings.getConsumedEnergy()` 返回值单位为 microwatt-seconds（uWs），表示从开机到当前时刻的累积能量，不是 microwatt-hours。

这套 API 读取的是能量快照（snapshot），不是实时订阅流。App 需要自行按时间间隔轮询，前后两次快照的 `getConsumedEnergy()` 做差值，才得到区间功耗。适合构建线上功耗自审计、热管理辅助判断等场景。[已验证: AOSP android-16.0.0_r1, android.os.PowerMonitor / android.os.PowerMonitorReadings / android.os.health.SystemHealthManager]

## 与其他机制的关系

Android 功耗模型与本书多个章节讨论的机制紧密关联：

- **CPU 调度（§5.1）**：调度器决定哪个进程在哪个核心上运行多久，直接影响 BatteryStats 中 CPU 时间的归属计算。EEVDF/CFS 的调度决策最终都会反映在功耗统计中。
- **EAS / PAS（§5.2）**：EAS 使用静态 Energy Model（EM）做开环预测——根据 EM 表估算任务迁移的能耗代价，选择最优核。截至目前公开的 AOSP 源码（android-16.0.0_r1）中，调度器路径（`find_energy_efficient_cpu` / `sched_energy_util`）仍走 EM 静态表计算，尚未发现从 ODPM / PowerStats HAL 实时读取功耗并反馈到调度的确定调用链。ADPF / CPU-GPU headroom 走的是 `Power HAL` 的 `getCpuHeadroom` / `getGpuHeadroom` 接口和 `PerformanceHintManager` hint session 路径，而 PowerMonitor / PowerStats 是能量观测路径。两条路径目前在公开源码层面暂未对接。[待验证: 如后续 CDD / source.android.com 或新 AOSP tag 补充了 ODPM→EAS 反馈链，可重新修订]
- **DVFS（§5.4）**：CPU 频率是 power_profile 中最详细的参数之一。DVFS 决定了 CPU 在哪个频率点运行，直接决定了该时刻的功耗估算值。
- **大小核架构（§5.3）**：异构 CPU 的功耗建模比同构 CPU 复杂得多，power_profile 中需要为每个集群提供独立的频率-电流对照表。
- **热管理（§5.5）**：热节流会强制降低 CPU 频率，间接降低功耗。但功耗估算系统本身不感知热状态——如果设备因过热而降频，power_profile 中对应高频的参数就不会被使用，导致估算的"总功耗"低于实际值。
- **ADPF（§5.9）**：Android 16 的 ADPF 通过 `PerformanceHintManager` 向系统上报帧负载和 deadlines，系统侧据此调整 CPU/GPU 频率和核心迁移。公开 API 层面，ADPF 与 ODPM / PowerStats 是两条独立路径：ADPF 走 `PerformanceHint` session，ODPM 走 `SystemHealthManager` / `PowerMonitor` 快照读取。两者是否在内核或 vendor 层面存在联动，目前缺少公开资料支撑。[待验证: ADPF hint session 是否间接利用 ODPM 数据做预防性降频，需后续 CDD / source.android.com 确认]
- **Android 功耗管理机制（§5.6）**：Doze、App Standby 等机制通过限制后台活动来降低功耗。这些限制的效果最终都会体现在 BatteryStats 的统计数据中。
- **Perfetto 工具链（§13.1）**：Perfetto 是功耗分析最重要的可视化工具之一，特别是配合 ODPM 数据源使用时。

## 版本演进

| Android 版本 | 功耗模型相关变化 |
|:---|:---|
| Android 5.0 (API 21) | BatteryStats 全面重构，引入基于 UID 的归属统计；Battery Historian 工具发布 |
| Android 6.0 (API 23) | Doze 模式引入，BatteryStats 开始记录 Doze 状态时长 |
| Android 7.0 (API 24) | 后台优化限制，影响 WakeLock 统计方式 |
| Android 8.0 (API 26) | 后台执行限制，后台服务功耗归属调整 |
| Android 9 (API 28) | App Standby Buckets 引入，功耗统计按 bucket 分组展示 |
| Android 10 (API 29) | `android.hardware.power.stats@1.0::IPowerStats` 引入，HIDL rail API 使用 `getRailInfo()` / `getEnergyData()` 读取实测能量 |
| Android 11 (API 30) | HIDL rail 视角继续沿用，Power rails 仍然是工具侧常见观测对象 |
| Android 12 (API 31) | AIDL `android.hardware.power.stats.IPowerStats` 加入，拆成 `EnergyConsumer` 与 `Channel` / `EnergyMeasurement` 两组对象 |
| Android 13 (API 33) | Framework 侧继续通过 `BatteryUsageStats` / `UidBatteryConsumer` 输出归属结果，方便 Settings 和 bugreport 读取 |
| Android 14 (API 34) | `CpuPowerCalculator`、`ScreenPowerCalculator` 等继续优先使用 hardware energy data，缺失时回退到 power-profile 估算 |
| Android 15 (API 35) | `PowerMonitor` / `SystemHealthManager` 公开 API 引入，支持 App 程序化查询能量快照；PAS 动态反馈路径目前缺少公开 AOSP 调用链证据（待验证） |
| Android 16 (API 36) | ADPF 与 ODPM 是否存在调度层联动，目前缺少公开 AOSP 源码或官方文档支撑（待验证）；Framework 进入过渡态，`BatteryUsageStatsProvider` 保留 `*PowerCalculator` 回退，同时调用 `PowerAttributor` 处理受支持组件 |
| Android 17 (API 37) | 功耗归因管线重构：`*PowerCalculator`（`CpuPowerCalculator`、`ScreenPowerCalculator` 等）从 `power/stats/` 移除，`BatteryUsageStatsProvider` 改为委托 `PowerAttributor`；默认实现 `MultiStatePowerAttributor` 配置 `processor/*PowerStatsProcessor`（`CpuPowerStatsProcessor`、`ScreenPowerStatsProcessor` 等）；`ScreenPowerStatsProcessor` 的屏幕分摊不再保留 `MIN_ACTIVE_TIME_FOR_SMEARING = 10min` 门槛；`shouldResetOnUnplugLocked()` 高电量阈值从硬编码 `>= 90` 改为 `BatteryStatsConfig.getHighBatteryLevelAfterCharge()` 配置化 |

## 常见问题与误区

### 误区一："电池设置里的 App 耗电百分比是精确的"

这个数字不是固定等于 `power_profile.xml` 的估算值。设置页展示的是 `BatteryUsageStats` 归属结果，某个组件如果拿到了 hardware energy data，Framework 会优先使用实测能量；缺失时才回退到 power-profile 或 controller/activity 估算。CPU、Screen、WiFi、Radio 等组件能否走哪条路，取决于设备 HAL 和统计能力。所以这个百分比更适合排序和定位，不适合当作实验室级精度的绝对值。

### 误区二："Coulomb Counter 能精确测量每个 App 的耗电"

Coulomb Counter 只能测量电池总出口的电流，它知道"过去一小时总共消耗了 300mAh"，但不知道这 300mAh 被谁消耗了。按 App 拆分的功能完全依赖 BatteryStats 的软件归属算法。Coulomb Counter 的价值是提供一个全局的校准基准。

### 误区三："App 完全在后台就不耗电"

即使 App 没有任何可见的 Activity，它也可能因为以下原因持续耗电：持有 WakeLock 阻止 CPU 休眠、注册了 GPS/传感器监听、后台网络活动维持 TCP 长连接、周期性的 JobScheduler 任务唤醒 CPU。BatteryStats 会忠实记录这些后台活动并归属到对应 App。在 Battery Historian 中，我们可以通过 "Userspace Wakelock" 和 "Network" 行来识别这类后台功耗。

### 误区四："高 CPU 使用率 = 高耗电"

CPU 使用率高不等于功耗高。关键在于 CPU 在哪个频率上运行。1GHz 上 100% 使用率的功耗可能只有 2GHz 上 50% 使用率的一半。这就是为什么 DVFS（§5.4）对功耗优化如此重要——让 CPU 跑在刚好够用的频率上，比降低 CPU 使用率更有效。

### 误区五："ODPM 是万能的功耗分析方案"

ODPM 提供的是 meter / rail / energy consumer 读数，不是自动给 `power_profile.xml` 做校准的开关。在支持的设备上，Framework 可以直接消费这些硬件能量数据，再生成 `BatteryUsageStats` 和 `UidBatteryConsumer`；缺少硬件数据时才回退到 power-profile 估算。ODPM 解决的是“有没有实测能量入口”，App 级别归属仍然要靠 BatteryStats / BatteryUsageStats 把共享资源和 UID 活动折算成结果。

## 参考资料

- AOSP power_profile.xml: `frameworks/base/core/res/res/xml/power_profile.xml`
- AOSP BatteryStatsImpl: `frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsImpl.java`
- AOSP BatteryUsageStatsProvider: `frameworks/base/services/core/java/com/android/server/power/stats/BatteryUsageStatsProvider.java`（Android 16 为 *PowerCalculator + PowerAttributor 过渡态；Android 17+ 委托 PowerAttributor）
- AOSP CpuPowerCalculator: `frameworks/base/services/core/java/com/android/server/power/stats/CpuPowerCalculator.java`（Android 5-16；Android 17+ 由 CpuPowerStatsProcessor 替代）
- AOSP ScreenPowerCalculator: `frameworks/base/services/core/java/com/android/server/power/stats/ScreenPowerCalculator.java`（Android 5-16；Android 17+ 由 ScreenPowerStatsProcessor 替代）
- AOSP PowerAttributor（Android 16+）: `frameworks/base/services/core/java/com/android/server/power/stats/PowerAttributor.java`
- AOSP MultiStatePowerAttributor（Android 16+）: `frameworks/base/services/core/java/com/android/server/power/stats/processor/MultiStatePowerAttributor.java`
- AOSP CpuPowerStatsProcessor（Android 17+）: `frameworks/base/services/core/java/com/android/server/power/stats/processor/CpuPowerStatsProcessor.java`
- AOSP ScreenPowerStatsProcessor（Android 17+）: `frameworks/base/services/core/java/com/android/server/power/stats/processor/ScreenPowerStatsProcessor.java`
- AOSP BatteryStatsConfig（Android 17+）: `frameworks/base/services/core/java/com/android/server/power/stats/BatteryStatsConfig.java`
- AOSP BatteryStatsService: `frameworks/base/services/core/java/com/android/server/am/BatteryStatsService.java`
- IPowerStats HAL (HIDL 1.0): `hardware/interfaces/power/stats/1.0/IPowerStats.hal`
- IPowerStats HAL (AIDL): `hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl`
- Android 电源概览: https://source.android.com/docs/core/power
- Battery Historian 工具: https://github.com/google/battery-historian
- Android Studio Power Profiler: https://developer.android.com/topic/performance/power
- Perfetto 功耗数据源: https://perfetto.dev/docs/data-sources/power
