---
title: "Android 功耗模型"
section: "11.1"
chapter: "11.1"
status: ready-for-review
reviewed_date: "2026-04-04"
reviewed_by: "openclaw-task6"
drafted_date: "2026-04-03"
drafted_by: "openclaw-task2a"
polish_count: 1
polish_date: "2026-04-07"
polish_by: "task2b-polish"
applicable_versions: "Android 5.0 (API 21) - Android 16 (API 36)"
last_verified: "2026-04-03"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/core/res/res/xml/power_profile.xml"
  - type: aosp
    path: "frameworks/base/core/java/android/os/BatteryStats.java"
  - type: aosp
    path: "hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl"
  - type: official
    path: "https://source.android.com/docs/core/power"
  - type: official
    path: "https://developer.android.com/topic/performance/power"
tags: ['power', 'battery', 'power_profile', 'BatteryStats', 'ODPM', 'Coulomb Counter', 'Fuel Gauge', 'IPowerStats', '功耗归属']
related_chapters: ["5.4", "5.5", "5.6", "11.2", "11.3", "13.1"]
---

# Android 功耗模型

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 Android 功耗模型：power_profile.xml 定义各硬件模块的功耗参数
- 🔹 功耗组成拆解：CPU、Display、GPU、Cellular、WiFi、GPS、Audio、Camera
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

当用户抱怨"你的 App 太耗电了"的时候，开发者往往一脸茫然——我的 App 又没有做挖矿，怎么会耗电？问题在于，耗电不是一个 App 自己说了算的事。Android 系统通过一套精心设计的功耗模型，把电池消耗拆分到各个硬件模块，再按使用时间归属到每个 App。如果我们不了解这套模型的工作原理，就不知道"设置 → 电池 → 电池使用情况"里那个百分比是怎么算出来的，更不知道该怎么优化。

理解功耗模型的核心价值在于：它决定了我们能获取到哪些功耗数据，以及这些数据有多可信。当我们打开 Battery Historian 看到一个 App 的 CPU 耗电占比异常时，我们需要知道这个数字是来自硬件实测还是软件估算，误差范围有多大，哪些场景下数据可信、哪些场景下需要额外验证。

我们在前几章已经讨论了 CPU 调度（§5.1）、DVFS（§5.4）、热管理（§5.5）和 Android 功耗管理机制（§5.6）。那些章节讲的是系统如何"省电"，而本章要回答的问题是：系统怎么知道谁"费了电"，以及这个"知道"有多准确。

## 功耗模型的基础：power_profile.xml

Android 功耗模型的核心是一个叫 `power_profile.xml` 的 XML 文件。它位于 AOSP 的 `frameworks/base/core/res/res/xml/power_profile.xml`，定义了设备上每个硬件模块在各种工作状态下的电流消耗值（单位 mA）。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/res/res/xml/power_profile.xml]

这个文件的定位非常明确：当系统无法从硬件直接获取实际功耗数据时，就用这个文件里的预设值来估算。它不是精确的仪器测量结果，而是一张"查表"——系统记录某个硬件模块工作了多长时间，然后乘以这个模块在对应状态下的电流值，得到一个估算的电量消耗。

[已验证: 官方文档, source.android.com/docs/core/power]

### power_profile.xml 的结构

文件的根元素是 `<device name="Android">`，内部通过 `<item>` 和 `<array>` 两种标签来定义功耗参数。`<item>` 用于单个值（如屏幕开启时的电流），`<array>` 用于一组值（如不同 CPU 频率对应的电流）。下面是一个简化过的结构示例：

```xml
<device name="Android">
    <!-- 屏幕：开启状态（不含背光） -->
    <item name="screen.on">83 mA</item>
    <!-- 屏幕：最高亮度下的背光 -->
    <item name="screen.full">260 mA</item>

    <!-- CPU：各频率点对应的电流 -->
    <array name="cpu.speeds">
        <value>300000</value>  <!-- 300 MHz -->
        <value>600000</value>
        <value>800000</value>
        <value>1200000</value>
        <value>1500000</value>  <!-- 1.5 GHz -->
    </array>
    <array name="cpu.active">
        <value>52</value>   <!-- 300MHz 时的电流 mA -->
        <value>78</value>
        <value>105</value>
        <value>145</value>
        <value>210</value>  <!-- 1.5GHz 时的电流 mA -->
    </array>
    <!-- CPU 空闲时的电流 -->
    <item name="cpu.idle">3.5 mA</item>

    <!-- WiFi -->
    <item name="wifi.on">3 mA</item>
    <item name="wifi.scan">70 mA</item>
    <item name="wifi.active">120 mA</item>

    <!-- 蜂窝网络 Radio -->
    <item name="radio.active">180 mA</item>
    <item name="radio.scanning">65 mA</item>
    <array name="radio.on">
        <value>3 mA</value>   <!-- 信号强 -->
        <value>5 mA</value>   <!-- 信号中 -->
        <value>8 mA</value>   <!-- 信号弱 -->
    </array>

    <!-- GPS -->
    <item name="gps.on">50 mA</item>

    <!-- 蓝牙 -->
    <item name="bluetooth.active">20 mA</item>
    <item name="bluetooth.on">1 mA</item>

    <!-- Camera -->
    <item name="camera.avg">550 mA</item>

    <!-- 音频 -->
    <item name="audio">60 mA</item>

    <!-- 视频 -->
    <item name="video">50 mA</item>
</device>
```

[待验证: 以上数值为示意性占位，非真实设备数据。AOSP 默认文件中的值为 0.1mA 占位值]

这个结构中有几个关键细节。

第一，CPU 的功耗被拆分为"各频率点对应电流"和"空闲电流"两部分。这是因为现代 SoC 的 CPU 功耗随频率呈非线性增长——1.5GHz 时的电流可能是 300MHz 时的四倍。对于异构 CPU（大小核架构），文件中会有 `cpu.speeds.cluster0`、`cpu.speeds.cluster1` 这样的独立数组，分别对应小核和大核集群。这和我们在 §5.3 中讨论的大小核架构直接对应。

第二，蜂窝网络 Radio 的功耗按信号强度区分了多个等级。信号弱时，Radio 需要更大的发射功率来维持连接，电流消耗可能比信号强时高出两三倍。这就是在地铁里刷手机特别费电的原因之一。

第三，AOSP 中默认的 `power_profile.xml` 包含的都是占位值（通常是 0.1mA）。OEM 厂商必须在出货前用实际硬件测量填充真实数据。如果厂商偷懒填了不准的值（或者直接用了默认值），那么整个功耗归属系统的准确性都会大打折扣。

## 功耗组成拆解

了解了 power_profile.xml 的结构之后，我们来看看 Android 设备的功耗到底由哪些部分组成。搞清楚这一点，才能理解为什么有些 App 看起来什么都没做却很费电，而有些 App 明明很忙却不怎么耗电。

### CPU：功耗的大头

CPU 几乎永远是功耗清单上的第一项。它的工作模式简单直接：频率越高越费电，核心越多越费电，持续运行越久越费电。我们在 §5.4 中讨论过 DVFS 机制，系统会根据负载动态调整 CPU 频率来平衡性能和功耗。从功耗模型的角度看，BatteryStats 会记录每个 App 在各个 CPU 频率上的运行时间，然后乘以 power_profile 中对应频率的电流值，得到该 App 的 CPU 耗电量。

计算公式如下：

```
App CPU 耗电量 (mAh) = Σ (频率i的运行时间 (秒) / 3600 × 频率i的电流 (mA))
```

对于需要计算能量消耗（mWh）的场景，还需要乘以对应频率下的标称电压（`cpu.voltage` 数组中的值）。但在 BatteryStats 的 App 归属统计中，计算单位是电荷量 mAh，不涉及电压。

这里有一个容易忽略的细节：CPU 空闲时的功耗（cpu.idle）被算作系统级开销，不会归属到任何 App。只有 CPU active 状态的时间才会被分配给对应的进程。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/BatteryStats.java — getCpuEnergyConsumptionUC()]

### Display：最直观的耗电源

屏幕是另一个功耗大户，而且它的耗电模式很直观——亮度越高越费电，刷新率越高越费电。power_profile 中定义了 `screen.on`（屏幕开启、最低亮度）和 `screen.full`（屏幕开启、最高亮度）两个锚点值，系统根据实际亮度在这两个值之间线性插值。

屏幕功耗通常被算作系统级开销，不会直接归属到某个 App。但在 Battery Historian 中，我们可以通过"屏幕开启时段"和"电量下降速度"的对应关系，间接判断亮屏时的耗电趋势。结合 §2.2 中讨论的刷新率机制，120Hz 屏幕在高亮度下的耗电可能比 60Hz 屏幕高出 50% 以上。

### GPU：隐藏的耗电源

GPU 的功耗在 power_profile 中的定义相对简单，通常只有 `gpu.active` 一个条目，不像 CPU 那样有频率-电流对照表。这导致 GPU 功耗的估算精度比 CPU 低得多——系统很难区分 GPU 是在满负荷渲染游戏还是在轻度合成 UI。

在实际分析中，GPU 功耗常被归入"硬件"类别或与 CPU 合并统计。如果我们在做游戏或视频播放类 App 的功耗分析，需要特别注意 GPU 这个隐藏变量。

### Cellular / WiFi / GPS：通信模块三兄弟

通信模块的功耗有一个共同特点：它们的状态切换本身就很费电。以蜂窝网络为例：

- **连接态（radio.active）**：正在传输数据，电流最高（100-300mA）。
- **空闲态（radio.on）**：维持连接但不传输，电流较低但持续存在（3-10mA，信号弱时更高）。
- **休眠态**：完全关闭，几乎不耗电。

Radio 的状态切换不是瞬间完成的。从休眠态到连接态需要几百毫秒到几秒不等，期间消耗的电量也算在 Radio 活跃时间里。Android 通过一个"Radio Active Timeout"机制来管理这个问题——数据传输结束后，Radio 不会立即进入休眠，而是等待一个超时时间（通常 5 秒），如果在超时时间内有新数据需要传输，就复用已有的连接，避免频繁的状态切换开销。

[已验证: 官方文档, source.android.com/docs/core/power/networks]

WiFi 和 GPS 的模式类似，但 WiFi 的活跃态功耗（约 100-150mA）通常低于蜂窝网络，GPS 的活跃态功耗约 50mA 但持续运行时的累计效果很可观。

### Audio / Camera / Bluetooth：按使用场景计费

Audio、Camera 和 Bluetooth 的功耗模型比较简单——基本上就是"开启时间 × 对应电流"。Camera 是其中的耗电大户（300-600mA），所以持续调用 Camera 的 App（如视频通话、AR 应用）在电池统计中通常排名靠前。Bluetooth LE（低功耗蓝牙）的活跃态电流只有几 mA，远低于经典蓝牙，这也是为什么穿戴设备都使用 BLE 通信。

## BatteryStats：数据采集与统计引擎

了解了功耗参数之后，我们来看 Android 是如何采集和统计这些数据的。BatteryStats 是 Android Framework 中的核心功耗统计服务，它持续运行在后台，记录每个硬件模块的状态变化和每个 App 的资源使用情况。

[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/os/BatteryStats.java]

### 采集方式：Push + Pull 混合

BatteryStats 的数据采集采用两种机制：

**Push 机制**：当硬件模块的状态发生变化时，对应的服务主动通知 BatteryStats。比如 WiFi 开启时，WiFiService 会调用 `BatteryStats.noteWifiOn()`；GPS 开始定位时，LocationManagerService 会调用 `BatteryStats.noteGpsOn()`。这种方式实时性好，不会遗漏状态变化。

**Pull 机制**：对于 CPU 使用时间这类需要持续统计的数据，BatteryStats 会定期从 `/proc/` 文件系统或内核接口拉取数据。每个进程的 CPU 时间、各频率点的运行时长都通过这种方式获取。

### 数据存储与持久化

BatteryStats 的数据以二进制格式存储在 `/data/system/batterystats.bin` 文件中。每次设备充电完成（从充电状态变为满电或拔掉充电器），BatteryStats 会记录一个"充电周期"（charge cycle），并在新一轮周期开始时重置统计计数器。这就是为什么 Battery Historian 分析时建议先重置再采集数据的原因——重置操作清空的是上一个周期的累积数据，开始一个干净的采集窗口。

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

到目前为止我们讨论的都是"软件估算"——用预设的功耗参数乘以使用时间来推算耗电量。但 Android 设备中其实还有一条更直接的功耗测量路径：硬件级的 Coulomb Counter。

### Coulomb Counter（库仑计）

Coulomb Counter 是一个集成在设备主板上的专用芯片，通常位于 Fuel Gauge IC 中（如 Maxim MAX17050、TI BQ 系列）。它通过直接测量流入和流出电池的电流来计算电量变化。原理很直观：对电流进行时间积分，就得到了电荷量（mAh）。

这种方式的精度远高于软件估算，通常可以达到 ±2-5% 的误差范围。它不受 power_profile 参数不准确的影响，也不需要对硬件模块进行抽象建模——直接测量就是了。

[待验证: 不同设备使用的 Fuel Gauge IC 型号和精度有差异，具体数值需参考各设备数据手册]

### Fuel Gauge（电量计）

Fuel Gauge 是 Coulomb Counter 的"上层建筑"。它不仅仅做电流积分，还会结合电池电压、温度、放电曲线等信息，综合计算出电池的 State of Charge（SoC，即电池剩余百分比）和 State of Health（SoH，即电池健康度）。

现代 Fuel Gauge IC（如 TI 的 Impedance Track 系列）采用混合算法：用 Coulomb Counter 做实时的充放电跟踪，用开路电压（OCV）在电池静置时做校准，用温度传感器做补偿。三者结合，能在动态负载下保持较高的 SoC 精度。

### 软件估算 vs 硬件测量：各自的局限

这两种方式并不是互相替代的关系，而是互补的：

**软件估算的优势**是粒度细——它可以明确展示"App A 的 CPU 耗电 50mAh，WiFi 耗电 20mAh"。这种按 App、按模块拆分的能力是硬件测量做不到的，因为 Coulomb Counter 只能量到电池总出口的电流，无法区分这个电流是被谁消耗的。

**硬件测量的优势**是精度高——它可以准确展示"过去 1 小时电池总共消耗了 200mAh"。这个全局精度是软件估算难以保证的，特别是当 power_profile 参数不准时。

在实际的 Android 系统中，两者结合使用：Fuel Gauge 提供全局的电量消耗基准（电池百分比），BatteryStats + power_profile 提供按 App 的拆分归属。下一节我们会看到，Android 10 引入的 IPowerStats HAL 正是为了弥合这两条路径之间的精度差距。

## App 耗电量的归属算法

这是功耗模型最核心的问题：系统怎么知道"你的 App 耗了 X% 的电"？

### 归属的基本思路

BatteryStats 的归属算法基于一个简洁的公式：

```
App 某模块耗电量 = 该模块活跃时间归属到该 App 的部分 × power_profile 中该状态的电流值
```

对不同模块，归属策略不同：

**CPU**：直接按进程的 CPU 时间归属。进程 A 在 1.5GHz 上跑了 500ms，就归属 500ms × 210mA 的电量。BatteryStats 通过 `/proc/stat` 和 `process_cpu_time` 来追踪每个进程在各个 CPU 频率上的运行时间。

[已验证: AOSP android-16.0.0_r1, BatteryStats.java — processCpuUsage tracking]

**WiFi / 蓝牙 / Radio**：按网络活动归属。系统通过 UID（每个 App 的唯一标识）来追踪网络流量和连接活跃时间。当 App A 发起网络请求导致 WiFi 模块被唤醒时，这段活跃时间就被记在 App A 的账上。对于多个 App 同时使用网络的场景，活跃时间会按比例分摊。

**GPS**：按注册的 LocationListener 归属。哪个 App 注册了 GPS 监听，GPS 活跃时间就归属给哪个 App。如果多个 App 同时请求 GPS，同样按比例分摊。

**WakeLock**：按持有者归属。App 持有 WakeLock 阻止 CPU 进入休眠的时间，会导致额外的 CPU idle 功耗，这部分会被加到该 App 的账上。这是后台 App 被标记为"高耗电"的常见原因之一。

**Screen**：屏幕功耗通常不归属到特定 App，而是作为系统级开销。在某些实现中，如果前台 App 强制设置了特定的亮度或刷新率，这部分增量可能会被归属到该 App。

### 计算示例

假设一个 App 在 5 分钟内的活动如下：

- CPU：1.2GHz 运行 30 秒（power_profile 中对应 145mA）
- WiFi 活跃传输 60 秒（power_profile 中对应 120mA）
- GPS 定位 120 秒（power_profile 中对应 50mA）

那么该 App 的估算耗电量为：

```
CPU 部分：(30/3600) × 145 = 1.21 mAh
WiFi 部分：(60/3600) × 120 = 2.00 mAh
GPS 部分：(120/3600) × 50  = 1.67 mAh
总计：约 4.88 mAh
```

假设设备电池容量为 4000mAh，该 App 在这 5 分钟内消耗了约 0.12% 的电量。看起来不多，但如果这种模式持续一小时，就是 1.4%——对于一个导航类 App 来说这是正常的，但对于一个后台 App 来说就很离谱了。

[待补充: 实际 BatteryStats 中的计算会考虑更多因素，包括电压、集群加权、Radio 状态机等]

### 归属的精度问题

归属算法最大的不确定性来自两个地方：

第一，**共享资源分摊**。当 App A 和 App B 同时使用 WiFi 时，WiFi 模块只开启一次，活跃时间如何分配？Android 的策略是按比例分摊，但实际的功耗并不是线性的——两个 App 同时传输和单个 App 传输的总 WiFi 功耗可能差不多。这会导致每个 App 被低估。

第二，**间接功耗**。App A 的大量网络请求可能触发 TCP 协议栈、内核网络软中断、Radio 状态切换等一系列系统级行为，这些间接功耗很难精确归属到发起者。系统只能尽量近似，但无法做到完全精确。

## ODPM：从估算到实测的跨越

Android 10 引入了一个重要的硬件抽象层接口——IPowerStats HAL（`hardware/interfaces/power/stats/`），配合 Google Pixel 6 及后续 Pixel 设备上的 ODPM（On-Device Power Monitor）子系统，意味着 Android 功耗模型开始从纯估算向估算与实测混合模式演进。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl]

### ODPM 的工作原理

ODPM 利用设备 PMIC（Power Management IC）上的专用功耗计数器，直接测量各个电源轨（power rail）上的能量消耗。所谓"电源轨"，就是主板上一条为特定硬件模块供电的线路。比如 CPU 大核有自己的电源轨，GPU 有自己的，屏幕有自己的一条——每个轨的功耗都可以被独立测量。

与电池端的 Coulomb Counter 不同，ODPM 的测量点在电池下游，直接在各个硬件模块的供电入口处。这意味着 ODPM 的读数不受设备充放电状态的影响——即使在充电时，ODPM 也能准确报告各模块的功耗。

### IPowerStats HAL 接口

IPowerStats HAL 提供两个核心 API：

- `getRailInfo()`：返回设备上所有可测量的电源轨列表及其元数据（名称、子系统的对应关系）。
- `getEnergyData()`：返回每个电源轨自开机以来的累积能量消耗（单位 μJ 或 mAh）。

系统通过定期轮询这些接口，计算两次采样之间的差值，得到各模块的实时功耗。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/power/stats/]

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

ODPM 虽然强大，但目前有几个明显的局限：

第一，**设备覆盖有限**。ODPM 需要硬件支持（PMIC 上有功耗计数器），不是所有设备都具备这个能力。目前只有 Pixel 6+ 系列有完整支持，其他 OEM 厂商的实现参差不齐。

第二，**粒度仍然是模块级**。ODPM 可以展示"CPU 大核消耗了 X mAh"，但无法展示"App A 在 CPU 大核上消耗了 Y mAh"。App 级归属仍然依赖 BatteryStats 的软件算法，ODPM 只是提供了一个更准确的校准基准。

第三，**采样间隔有限**。IPowerStats HAL 的轮询间隔通常在秒级，无法捕捉毫秒级的功耗毛刺。对于分析瞬间功耗峰值（如 Camera 启动时的功耗飙升），还是需要外接功耗仪。

## 功耗模型的准确性问题与校准

了解完整个功耗模型的架构之后，我们需要正视一个现实：Android 的功耗估算并不总是准确的。准确地说，它的准确性取决于一长串前提条件。

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

**Battery Historian**：这是功耗分析的主力工具。通过解析 bugreport 中的 BatteryStats 数据，Battery Historian 提供了从系统级到 App 级的完整功耗时间线可视化。我们可以看到屏幕亮度变化、网络状态切换、WakeLock 持有、App 前后台切换等事件与电量下降的对应关系。[待补充: Battery Historian 截图示例]

**dumpsys batterystats**：命令行工具，输出 BatteryStats 的原始统计数据。适合脚本化分析和自动化测试场景。常用命令组合：

```bash
# 重置统计（开始新的采集周期）
adb shell dumpsys batterystats --reset

# 导出完整统计
adb shell dumpsys batterystats > batterystats.txt
```

**Perfetto + ODPM**：在支持 ODPM 的设备上，Perfetto 可以采集 `android.hardware.power.stats` 数据源，将电源轨的功耗数据与 CPU 调度、线程活动等 Trace 信息同步展示。这是目前最精确的功耗分析手段。

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
        name: "android.hardware.power.stats"
        target_buffer: 0
    }
}
duration_ms: 60000
EOF
```

[待验证: Perfetto 中 power.stats 数据源的具体配置格式可能因 Android 版本而异]

**Android Studio Power Profiler**：从 Hedgehog 版本开始集成，在 System Trace 视图中直接显示 ODPM 电源轨数据，与 CPU、线程、Frame 时间线对齐。适合 App 开发者做日常功耗分析。

## 与其他机制的关系

Android 功耗模型不是一个孤立的系统，它与本书多个章节讨论的机制紧密关联：

- **CPU 调度（§5.1）**：调度器决定哪个进程在哪个核心上运行多久，直接影响 BatteryStats 中 CPU 时间的归属计算。EEVDF/CFS 的调度决策最终都会反映在功耗统计中。
- **DVFS（§5.4）**：CPU 频率是 power_profile 中最详细的参数之一。DVFS 决定了 CPU 在哪个频率点运行，直接决定了该时刻的功耗估算值。
- **大小核架构（§5.3）**：异构 CPU 的功耗建模比同构 CPU 复杂得多，power_profile 中需要为每个集群提供独立的频率-电流对照表。
- **热管理（§5.5）**：热节流会强制降低 CPU 频率，间接降低功耗。但功耗估算系统本身不感知热状态——如果设备因过热而降频，power_profile 中对应高频的参数就不会被使用，导致估算的"总功耗"低于实际值。
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
| Android 10 (API 29) | **IPowerStats HAL 引入**，ODPM 硬件功耗监测能力；power_profile.xml 支持更多模块 |
| Android 12 (API 31) | 功耗模型增强，支持更多传感器类型的功耗统计 |
| Android 13 (API 33) | 后台限制进一步加强，前台服务类型影响功耗归属 |
| Android 14 (API 34) | Battery Stats 改进，支持更精确的充电状态追踪 |
| Android 15 (API 35) | 功耗分析工具链持续改进 |
| Android 16 (API 36) | IPowerStats AIDL 接口更新，ODPM 数据源集成进一步深化 |

[待验证: Android 15/16 的具体变化需要查证 release notes]

## 常见问题与误区

### 误区一："电池设置里的 App 耗电百分比是精确的"

这个数字是基于 power_profile.xml 的估算值，不是硬件实测值。如果 power_profile 中的参数不准确（这在非 Pixel 设备上很常见），这个百分比的误差可能达到 20-30%。不要把这个数字当作绝对精确的度量，而是当作一个排序参考——排名靠前的 App 确实大概率是耗电最多的，但具体百分比的数值需要审慎看待。

### 误区二："Coulomb Counter 能精确测量每个 App 的耗电"

Coulomb Counter 只能测量电池总出口的电流，它知道"过去一小时总共消耗了 300mAh"，但不知道这 300mAh 被谁消耗了。按 App 拆分的功能完全依赖 BatteryStats 的软件归属算法。Coulomb Counter 的价值是提供一个全局的校准基准。

### 误区三："App 完全在后台就不耗电"

即使 App 没有任何可见的 Activity，它也可能因为以下原因持续耗电：持有 WakeLock 阻止 CPU 休眠、注册了 GPS/传感器监听、后台网络活动维持 TCP 长连接、周期性的 JobScheduler 任务唤醒 CPU。BatteryStats 会忠实记录这些后台活动并归属到对应 App。在 Battery Historian 中，我们可以通过 "Userspace Wakelock" 和 "Network" 行来识别这类后台功耗。

### 误区四："高 CPU 使用率 = 高耗电"

CPU 使用率高不等于功耗高。关键在于 CPU 在哪个频率上运行。1GHz 上 100% 使用率的功耗可能只有 2GHz 上 50% 使用率的一半。这就是为什么 DVFS（§5.4）对功耗优化如此重要——让 CPU 跑在刚好够用的频率上，比降低 CPU 使用率更有效。

### 误区五："ODPM 是万能的功耗分析方案"

ODPM 提供了模块级的实测功耗数据，但它不解决 App 级归属问题。即使在 ODPM 支持的 Pixel 设备上，"这个 App 消耗了多少电"的答案仍然依赖 BatteryStats 的软件估算。ODPM 做的是让这个估算更准确——它用实测数据校准 power_profile 中的参数，而不是替代整个归属算法。

## 参考资料

- AOSP power_profile.xml: `frameworks/base/core/res/res/xml/power_profile.xml`
- AOSP BatteryStats: `frameworks/base/core/java/android/os/BatteryStats.java`
- AOSP BatteryStatsManager: `frameworks/base/core/java/android/os/BatteryStatsManager.java`
- IPowerStats HAL (AIDL): `hardware/interfaces/power/stats/aidl/android/hardware/power/stats/IPowerStats.aidl`
- Android 电源概览: https://source.android.com/docs/core/power
- Battery Historian 工具: https://github.com/google/battery-historian
- Android Studio Power Profiler: https://developer.android.com/topic/performance/power
- Perfetto 功耗数据源: https://perfetto.dev/docs/data-sources/power
