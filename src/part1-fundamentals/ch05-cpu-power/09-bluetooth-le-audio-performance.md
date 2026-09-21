---
title: Bluetooth LE Audio 延迟与功耗性能
chapter: '5.9'
section: '5.9'
status: finalized
applicable_versions: Android 13 (API 33) - Android 17 (API 37)
last_verified: '2026-08-22'
last_source_verified_at: '2026-08-22'
last_verified_against: Android Core Specification 5.4, AOSP android-17.0.0_r1
confidence: medium-high
consolidated_from:
- src/part1-fundamentals/ch05-cpu-power/5.23-android17-background-audio-hardening-leaudio-power-source.md
sources:
- type: official
  path: developer.android.com/about/versions/13/features (LE Audio support)
- type: official
  path: source.android.com/docs/core/connect/bluetooth (LE Audio, Hearing aid BLE)
- type: spec
  path: Bluetooth Core Specification 5.4 (LE Audio, LC3, CIS/BIS)
- type: aosp
  path: packages/modules/Bluetooth/android/app/src/com/android/bluetooth/le_audio/
- type: aosp
  path: packages/modules/Bluetooth/system/bta/le_audio/codec_manager.cc
- type: aosp
  path: hardware/interfaces/bluetooth/audio/aidl/android/hardware/bluetooth/audio/SessionType.aidl
- type: aosp
  path: system/media/audio/include/system/audio-base-utils.h (AUDIO_DEVICE_OUT_BLE_HEADSET, AUDIO_DEVICE_OUT_BLE_SPEAKER, AUDIO_DEVICE_OUT_BLE_BROADCAST, AUDIO_DEVICE_OUT_BLE_HEARING_AID, AUDIO_DEVICE_OUT_BLE_CENTRAL)
tags:
- bluetooth
- le-audio
- lc3
- latency
- power
- audio
- isochronous
related_chapters:
- '1.20'
- '5.7'
- '11.4'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
last_deep_review_at: '2026-08-22T15:48:00+08:00'
last_deep_review_run_id: 20260822-154453-deep-review-fc34580b
---

# Bluetooth LE Audio 延迟与功耗性能

Android 13（API 33）加入了系统级 LE Audio 支持。到 Android 17（API 37），AOSP 仍同时支持 Classic Audio（传统 Bluetooth Classic 音频）与 LE Audio：用于媒体播放的 A2DP、用于通话的 HFP、LE Audio 单播和 LE Audio 广播，会根据设备能力、音频场景及系统策略共存。过渡期内，双模耳机仍很常见，不能把 LE Audio 理解成系统会无条件淘汰 Classic Audio。

LE Audio 的性能由整条音频路径共同决定：LC3 编解码、AudioFlinger 缓冲、Bluetooth Audio HAL（硬件抽象层）数据路径、ISO（等时传输）调度、射频环境和耳机端渲染，都会带来延迟与功耗。只看到“BLE”“7.5 ms 帧”或“硬件 offload（把部分处理交给专用硬件）”，不足以判断某个设备一定低延迟或一定省电。

平台源码锚点为 AOSP `android-17.0.0_r1`。LE Audio 的 Controller（蓝牙控制器）与 vendor（芯片或设备厂商）实现高度依赖芯片和固件；`android17-6.18-2026-06_r6` 内核标签也没有规定一套跨设备通用的 LC3、ISO 或功耗实现。因此，分析时要区分 AOSP 可以证明的系统边界与必须在设备上实测的行为。

## 先建立协议模型

### GAF、BAP 与控制服务

Bluetooth LE Audio 位于 Generic Audio Framework（GAF，通用音频框架）中。以下协议和服务分别负责能力、状态与控制：

| 组件 | 职责 | 对性能分析的意义 |
|---|---|---|
| BAP（Basic Audio Profile） | 定义单播、广播的音频流配置和过程 | 决定能力发现、Codec 与 QoS（服务质量）配置的基本规则 |
| PACS（Published Audio Capabilities Service） | 发布设备支持的 Codec 能力和可用音频上下文 | 配置只能从双方兼容的能力集合中选择 |
| ASCS（Audio Stream Control Service） | 管理单播 ASE 状态 | 流启动、停止和重配置需要经过状态迁移 |
| CAP（Common Audio Profile） | 协调一个或多个设备上的音频过程 | 左右耳、多设备同步不能只看单条链路 |
| VCS / VOCS | 音量和通道偏移控制 | 属于控制面，不应和媒体数据路径混在一起计时 |
| MCS / TBS | 媒体与电话控制 | 播放控制和音频承载可以走不同协议过程 |

ASE（Audio Stream Endpoint，音频流端点）的状态通常依次经过 Idle、Codec Configured、QoS Configured、Enabling、Streaming、Disabling 和 Releasing。首次建流、复用已有配置、切换音频上下文或改变 Codec/QoS 时，经过的步骤可能不同。看到一次启动耗时后，要先确认测量对象是首次连接、已连接后的建流，还是已有 CIG/CIS 的恢复。

### CIS/CIG 与 BIS/BIG

LE Audio 使用 Isochronous Transport（等时传输）承载必须按时送达的音频数据：

- **CIS（Connected Isochronous Stream）**用于单播，一个或多个 CIS 组成 CIG（Connected Isochronous Group）。CIS 与 ACL（设备之间的基础数据连接）关联，由 ACL 承载建立和控制过程；ACL 丢失时，关联的 CIS 也会终止。
- **BIS（Broadcast Isochronous Stream）**用于广播，一个或多个 BIS 组成 BIG（Broadcast Isochronous Group）。广播源通过扩展广播和周期广播公布同步信息与 BASE（描述广播音频配置的数据），接收端随后同步 BIG。

单播接收端可以确认链路层传输，Controller 可在已经分配的子事件时隙内安排重传。广播没有面向每个接收端的确认；广播源可以配置重复、交织或预传输来提高抗干扰能力，却无法根据某个接收端的丢包情况单独重发。丢包后的听感还取决于 LC3 的丢包隐藏、耳机缓冲和连续丢包长度，不能写成“丢一包就必然出现一次可闻断音”。

两个模式的扩展性也不同：

- 广播发送端的空口计划不会随着收听人数线性增加；
- 单播增加设备或音频方向时，通常会增加 CIS、子事件或控制开销；
- 广播接收端还要执行扫描、周期广播同步和 BIG 同步，这些阶段也会产生成本，所以“广播接收一定比单播省电”没有通用依据。

### LC3 的能力需要协商

LC3（Low Complexity Communication Codec）是 LE Audio 基础音频配置要求支持的标准 Codec。设备还可以支持其他 Codec，但通信双方至少要围绕标准能力完成互操作。Android 17 的 LE Audio 类型定义包含以下独立字段：

- sampling frequency；
- frame duration；
- audio channel allocation；
- octets per codec frame；
- codec frame blocks per SDU，其中 SDU（Service Data Unit）是交给等时链路传输的服务数据单元。

LC3 常见帧时长为 7.5 ms 和 10 ms。帧时长只是一个 Codec 参数，不能直接当作算法总延迟或端到端延迟。讨论码率时，也必须同时给出采样率、每帧字节数、每个 SDU 的帧块数和声道数，不能只列一个所谓的“LC3 固定范围”。

同理，LC3 与 SBC 的 CPU MIPS（每秒百万条指令，用于描述计算量）、MOS（Mean Opinion Score，主观音质评分）或耗电量，都依赖实现、配置和测试方法。在 Host（主机侧软件栈）上用软件运行、交给音频 DSP、Controller 或 vendor offloader，可能得到不同结果。没有目标芯片、编译选项、音频配置和功耗仪器时，不应填写看似精确的跨设备对比表。

## 延迟要按测量对象拆开

讨论“蓝牙延迟”前，至少要选定以下一种指标：

| 指标 | 起点与终点 | 适用问题 |
|---|---|---|
| 冷启动延迟 | 用户操作或播放请求，到耳机首次出声 | 首次连接、服务发现、建流是否过慢 |
| 已连接启动延迟 | 已完成 ACL/GATT（Generic Attribute Profile，通用属性配置文件）连接后开始播放，到首次出声 | ASCS、CIG/CIS 与音频路由开销 |
| 稳态单向延迟 | 手机音频时间点，到耳机声学输出 | 视频同步、乐器监听、游戏反馈 |
| 双向往返延迟 | 手机发声，经远端采集后返回手机 | VoIP、游戏语音、交互式音频 |
| 路由切换间隙 | 旧路由最末帧，到新路由第一帧 | A2DP/LE Audio 或扬声器/耳机切换 |
| 抖动与 glitch（爆音或短暂中断） | 稳态延迟分布、缓冲欠载和丢帧 | 射频干扰、调度和缓冲稳定性 |

一次稳态单向延迟可以按以下预算理解：

`应用/AudioTrack 缓冲 + AudioFlinger/HAL 缓冲 + 编码与组帧 + ISO 发送窗口 + Presentation Delay + 耳机解码/后处理/渲染`

上式中的每一项都可能跨越一个或多个音频周期。Presentation Delay（规定接收端播放时刻的呈现延迟）还可能为了多设备同步和接收端缓冲而增加。用 7.5 ms 或 10 ms 的 LC3 帧长直接推导“总延迟 20–40 ms”，会漏掉手机和耳机两端的大量缓冲，也会忽略 QoS 与射频重传。

下面的图用于区分 Android 侧、Controller 侧和耳机侧的延迟来源：

```mermaid
flowchart LR
    A["应用：AudioTrack / AudioRecord"] --> B["AudioFlinger 与 Audio Policy"]
    B --> C["Audio HAL / Bluetooth Audio Provider"]
    C --> D["Host LC3 或硬件 offload"]
    D --> E["Bluetooth 栈：BAP / ASCS / ISO 数据路径"]
    E --> F["Vendor HAL 与 Controller"]
    F --> G["CIS / BIS 空口"]
    G --> H["耳机 Controller 与抖动缓冲"]
    H --> I["LC3 解码、DSP 后处理与扬声器"]
```

这条路径还分为控制面和数据面：ASCS/PACS 负责能力协商与状态管理，PCM（未压缩音频采样）或编码帧则通过选定的 Bluetooth Audio 数据路径传输。排障时应先判断时间消耗位于建流控制过程，还是 Streaming 之后的数据传输与渲染过程。

### Codec 与 QoS 参数怎样改变结果

| 参数 | 主要影响 | 常见代价 |
|---|---|---|
| frame duration | Codec 帧积累周期、调用频率 | 更短周期可能增加调度与包头开销 |
| octets per codec frame | 音质、码率和单帧负载 | 更大负载增加空口占用 |
| blocks per SDU / SDU interval | 组帧和发送节奏 | 聚合可减少调用次数，也会增加等待 |
| PHY（物理层模式） | 每次发送的空口时间和链路预算 | 2M PHY 传输更快，覆盖和干扰条件仍需实测 |
| BN / NSE（每个事件的数据突发数 / 子事件数） | 每个等时事件的数据与子事件安排 | 资源增加会占用更多射频时间 |
| RTN / FT（重传次数 / Flush Timeout） | 单播可靠性、可用重传窗口和最大时限 | 可靠性、延迟、共存和功耗互相制约 |
| Presentation Delay | 接收端何时播放 | 增大可换取同步与抗抖动余量 |
| CIS/BIS 数量与方向 | 多声道、左右耳和双向语音 | 增加调度、编码和空口资源 |

`RTN=2` 不能简单解释为“任何包最多重传两次后，延迟固定增加多少”。实际计划还受 BN、NSE、FT、PHY、PDU（Protocol Data Unit，协议数据单元）分段和 Controller 调度约束。调参时要查看最终 HCI（Host Controller Interface，主机控制器接口）配置与抓包结果，不能只看上层期望值。

### Android 没有公开的“一键 7.5 ms 游戏模式”

Android 17 的 LE Audio transport 提供了 `SetLatencyMode()`：它接收 `FREE`、`LOW_LATENCY`、动态空间音频软件和硬件等枚举，并映射到内部 `DsaMode`。源码没有把其中某个枚举直接映射成 7.5 ms LC3 配置，也没有承诺端到端延迟低于某个固定值。

普通应用设置 `AudioAttributes` 或游戏 `usage` 后，Audio Policy、Bluetooth 栈和设备能力仍会共同决定路由与配置。耳机厂商提供的 Gaming Mode 也可能改变私有缓冲、Codec 配置或射频策略。测试报告应记录最终协商参数，避免把产品模式名称当成协议参数。

## Android 17 的系统路径

### 控制路径

AOSP 的通用 Bluetooth 调用链如下：

1. Framework API 通过 Binder 进程间通信调用 Bluetooth 进程；
2. `packages/modules/Bluetooth/android/app` 实现 Profile Service；
3. Java 层通过 JNI（Java Native Interface）进入 `packages/modules/Bluetooth/system`；
4. Native BTA LE Audio 代码完成 PACS、ASCS、CAP、单播和广播状态处理；
5. Bluetooth HAL 与 vendor Controller 交换 HCI 命令、事件及数据。

在 `android-17.0.0_r1` 中，关键位置包括：

- `android/app/src/com/android/bluetooth/le_audio/LeAudioService.java`；
- `android/app/jni/com_android_bluetooth_le_audio.cpp`；
- `system/bta/le_audio/`；
- `system/audio_hal_interface/aidl/le_audio_software_aidl.cc`；
- `hardware/interfaces/bluetooth/audio/aidl/`。

`LeAudioService` 管理组、活跃输入/输出设备、广播与单播切换等 Framework 状态。Codec 能力选择、CIG/CIS 和 ASE 状态由 Native LE Audio 代码继续处理。如果把 `LeAudioService` 写成直接“注册 Audio Provider 并独自决定所有 LC3 参数”，就会忽略 Audio Framework、Bluetooth Audio HAL 与 Native 栈各自承担的工作。

### 音频数据路径

Android 17 的 `SessionType.aidl` 明确区分了：

- LE Audio 单播软件编码与软件解码；
- LE Audio 单播硬件 offload 编码与解码；
- LE Audio 广播软件编码与硬件 offload 编码；
- 广播解码和 peripheral offload（把部分数据处理放到外设侧）等路径。

在软件路径中，Bluetooth 栈负责相应的编解码和媒体数据处理；硬件 offload session 主要承载控制，数据和 Codec 工作由平台硬件实现负责。AOSP `codec_manager.cc` 还区分 `CodecLocation::HOST` 与 `CodecLocation::ADSP`（音频 DSP），并在检查设备属性和 HAL 能力后才启用 offload。源码中还保留了“offload 不支持某项配置时如何切换”的待完善点，因此不能因为“设备有 DSP”就断定当前音频流已经 offload。

### 音频设备类型

Android 17 `system/media/audio/include/system/audio-base-utils.h` 中，与本章媒体播放、耳机和广播路由直接相关的输出设备类型包括：

- `AUDIO_DEVICE_OUT_BLE_HEADSET`；
- `AUDIO_DEVICE_OUT_BLE_SPEAKER`；
- `AUDIO_DEVICE_OUT_BLE_BROADCAST`。

同一枚举还包含 `AUDIO_DEVICE_OUT_BLE_HEARING_AID` 与 `AUDIO_DEVICE_OUT_BLE_CENTRAL` 等 BLE 相关类型；排查时应按具体路由类型和 Profile 状态归类，不要把所有 BLE 输出合并成 headset、speaker 或 default。广播设备不是 `AUDIO_DEVICE_OUT_DEFAULT`。应用公开 API 侧可用 `AudioDeviceInfo.TYPE_BLE_HEADSET` 等类型识别设备，实际路由仍由 Audio Policy 和用户选择决定。

### 普通应用能控制到哪一层

媒体应用通常继续使用 `AudioTrack`、Media3 或其他媒体 API 播放。通信应用使用 `AudioManager.setCommunicationDevice()` 选择系统已提供的通信设备，并在结束后调用 `clearCommunicationDevice()`。应用不应通过已弃用的 SCO 开关控制 LE Audio 路由；SCO 属于 HFP/Classic 语音路径。

`BluetoothLeAudio` 是 Bluetooth Profile proxy（访问系统 Profile 服务的代理对象）。Android 17 SDK 中的公开接口包括查询已连接设备、连接状态、组 ID 和已连接组的 lead device（组内代表设备）；`getActiveDevices()`、`connect()`、`disconnect()`、Codec 偏好和许多组控制接口则带有 `@Hide`、`@SystemApi` 或 `BLUETOOTH_PRIVILEGED` 限制。

旧接口列表中的 `setConnectionState()` 与 `getAudioGroupOutType()` 并不是 Android 17 的公开方法。

下面的示例用于在应用侧判断手机是否声明 LE Audio 与广播源能力：

```kotlin
val adapter = getSystemService(BluetoothManager::class.java).adapter

val unicastSupported =
    adapter.isLeAudioSupported == BluetoothStatusCodes.FEATURE_SUPPORTED
val broadcastSourceSupported =
    adapter.isLeAudioBroadcastSourceSupported == BluetoothStatusCodes.FEATURE_SUPPORTED
```

这两个方法返回状态码，不返回布尔值；蓝牙关闭时还可能返回错误码。手机报告支持，也不代表当前耳机、通信双方的 Profile、区域配置和产品 UI 已经满足目标场景。应用仍要处理功能不可用与路由变化。

### 路由与切换延迟

当 A2DP 与 LE Audio 都可用时，Android 会结合设备能力、用户选择、音频策略和 Profile 状态决定活跃路由。不能概括为“Android 14 起总是优先 LE Audio”，也没有“当前内容格式不兼容就固定回退 A2DP”的通用公开规则。应用提交给 AudioFlinger 的 PCM 或媒体解码结果，与蓝牙空口使用的 Codec 属于两个层次。

一次切换间隙可能包含：

- 旧输出暂停、drain（播放完缓冲数据）或 flush（丢弃缓冲数据）；
- 新设备变为 active route（当前输出路由）；
- Audio Policy 重新打开输出；
- ASCS/CIG/CIS 建立或恢复；
- 新路径预填缓冲；
- 耳机在 Presentation Delay 后开始渲染。

这些步骤是否发生、是否并行、是否复用已有连接都由当次状态决定。300–800 ms 之类的固定范围只能作为某组设备的测试结果，不能标成 Android 17 平台保证。

## 功耗：看执行位置和射频计划

LE Audio 的手机端功耗可以粗略拆成：

`音频前后处理 + Codec + 内存搬运 + AP/DSP 唤醒 + Controller 基础功耗 + ISO 空口时间 + Wi-Fi/蓝牙共存代价`

其中 AP 指应用处理器，DSP 指数字信号处理器。耳机端还要计入：

`接收/发送射频 + LC3 + 抖动缓冲 + ANC（主动降噪）/通透/空间音频 DSP + 功放与传感器`

“LE”这个名字不能替代测量。影响结果的主要问题包括：

1. **Codec 在哪里运行**：Host 软件编码可能周期性唤醒 AP；ADSP 或其他 offloader 可以减少 AP 工作，但控制、缓冲和数据搬运成本仍然存在。
2. **发送了多少流**：左右耳独立流能改善同步与拓扑，也可能增加并行 Codec 实例和空口资源。
3. **可靠性配置怎样取舍**：更高重复或重传预算可改善恶劣链路，却会增加射频活动。
4. **是否双向**：通话和游戏语音同时包含下行播放与上行麦克风，不能拿它与单向音乐直接对比。
5. **是否命中共存问题**：2.4 GHz Wi-Fi、人体遮挡、手机握持和左右耳位置都可能改变丢包与功耗。
6. **耳机功能是否相同**：ANC、头部跟踪、麦克风和后处理常比协议差异更显著。

Classic TWS（真无线立体声）常采用主副耳中继，LE Audio 多流则允许手机分别向左右设备发送音频。它消除了某些中继拓扑的限制，但手机需要调度多条 CIS。整机是否省电取决于手机与耳机两端的实现，无法只根据拓扑判断。

### ISO 与系统 idle

Controller 具备独立的定时与射频调度能力，不要求 AP 在每个 CIS/BIS event 都运行。Host 软件路径可能按音频批次唤醒；offload 路径可以让 AP 保持更长的 idle（空闲）时间，但唤醒频率取决于缓冲和具体实现，不能根据 10 ms 帧长直接写成“AP 固定以 100 Hz 唤醒”。

维持 Bluetooth 连接也不表示 Android 设备被禁止进入某个名为“Deep Doze”的状态。活跃音频、音频 wakelock（唤醒锁）、应用前后台状态和系统电源策略会共同影响 suspend/idle。要判断 LE Audio 是否让 AP 退出深 idle，应查看 trace 中的调度、wakeup source（唤醒来源）、AudioFlinger 周期和电源轨数据。

Controller 重传主要消耗 Controller 和射频资源。它也可能通过数据短缺、状态事件或 Host 路径间接改变 AP 负载，但不能笼统写成“与 CPU DVFS 完全无关”。CPU 频率只反映其中一部分成本。

Android 17 的 Bluetooth 栈还会在 suspend 场景管理 LE background scan（后台扫描），并根据 Controller/offload 能力决定哪些扫描任务可以留在硬件执行。看到扫描在灭屏后减少，不能直接归因于 LE Audio Codec；还要核对扫描发起方（scan client）、硬件 offload filter（卸载过滤器）、设备 idle 状态与 active audio group。

HFP active-device handover 属于 Classic 通话路径，不应和 LE Audio route 切换合并成一条时延结论。

### 如何做可比较的功耗实验

至少固定以下条件：

- 同一手机构建、耳机固件、音量、曲目和播放时长；
- 相同采样率、声道、音频上下文与上/下行方向；
- 相同屏幕、网络、Wi-Fi 频段、信号强度和环境温度；
- 相同 ANC、空间音频、头部跟踪与佩戴传感器状态；
- 先确认当前采用 Host 还是 offload 路径，再比较 A2DP 与 LE Audio；
- 同时记录丢包、重传和 glitch，避免把牺牲可靠性换来的低功耗当成优化收益。

手机侧优先使用外部电源监测或设备电源轨；耳机侧需要夹具、电池电量计或厂商遥测。`batterystats` 适合观察系统归因和长期趋势，却很难单独分离几十毫秒周期内的 Codec 与射频成本。如果 Pixel 电流范围不同时说明设备、固件、测量仪器和置信区间，就不能作为通用参考数据。

## 广播音频与 Auracast

Auracast 是 Bluetooth Broadcast Audio 的品牌名称。广播源创建 BIG/BIS，并通过广播公告和周期广播发布同步信息；接收端或 Broadcast Assistant（广播助手）发现来源后，帮助 Broadcast Sink（广播接收设备）加入。

性能分析需要关注：

- 扫描到公告的时间；
- 周期广播同步和 BIG 同步时间；
- BASE 解析及 Codec 配置；
- BIS 数量、BN、NSE、IRC（立即重复次数）、PTO（预传输偏移）与 Presentation Delay；
- 加密广播的 Broadcast Code 处理；
- 丢包隐藏和多接收端同步误差。

BIS 没有针对每个接收端的 ACK（确认响应）。它可以用重复和预传输增加时间/频率分集；PTO 等配置也可能增加延迟。发送端不需要随着接收人数增加而逐个维护媒体链路，但不能据此声称“有 0 个或 100 个接收端时，手机整机功耗完全相同”，因为扫描、UI、控制过程和产品实现都可能变化。

Android 17 源码中的 `BluetoothLeBroadcast` 与 `BluetoothLeBroadcastAssistant` 是 `@SystemApi`，同时带有 `@Hide`；普通第三方应用没有一套等价的公开控制接口。`AudioManager.setBluetoothScoOn()` 已弃用，而且控制的是 SCO/HFP，不用于 Auracast。产品实现应使用平台提供的系统 UI、受支持角色和相应的 Bluetooth Profile 接口。

## HAP 与 ASHA 要分开

ASHA（Audio Streaming for Hearing Aids）早于标准 LE Audio，本身就运行在 BLE 上。Android 的 ASHA 设计使用 GATT 控制，并通过 LE L2CAP CoC（面向连接的逻辑信道）传输音频；CoC 的弹性缓冲能抵抗部分丢包，也会增加延迟。ASHA 没有从助听器返回手机的音频 backlink，通话上行使用手机麦克风。

HAP（Hearing Access Profile）属于标准 LE Audio/GAF，使用 LE Audio 的能力、控制和 ISO 音频机制，可以支持更完整的通话与 VoIP 场景。不能把它描述成“用 BLE 替代 Classic ASHA”，因为 ASHA 本身已经使用 BLE。Android 需要兼容旧有 ASHA 设备，同时支持基于 LE Audio 的 HAP 设备。

Android 13 提供 LE Audio 基础支持不代表所有 Android 13 设备都具备 HAP、广播或双向高采样率能力。助听场景对声学延迟、左右同步、丢包、麦克风路径和电池寿命都更敏感，20–40 ms 或固定省电比例仍需在目标产品上验证。

## Android 13 到 Android 17 的边界

| 版本 | 可确认的变化 |
|---|---|
| Android 13 / API 33 | Android 加入内建 LE Audio 支持；硬件与产品仍需声明相应能力 |
| Android 14 / API 34 | Telecom/VoIP（网络语音通话）路由 API 继续演进；不能由此推出固定的 LE Audio 7.5 ms 模式 |
| Android 15–16 | 中间版本不能单凭系统版本推断广播角色、低延迟配置或 HAP 能力，仍须查询设备能力和对应版本 API |
| Android 17 / API 37 | AOSP 同时存在单播/广播的软件、硬件 offload 与 peripheral 数据路径 |

Android 17 还重构了 Audio Managed SCO，使 SCO 的启停更多由 Audio Framework 统一管理。该变化面向 HFP/SCO，不能作为“LE Audio 延迟链路在 Android 17 被重写”的证据。

## 诊断与测量

### 第一步：确认能力、路由与 Profile 状态

下面的命令用于采集系统可见的 Bluetooth 和音频状态：

```bash
adb shell dumpsys bluetooth_manager
adb shell dumpsys audio
adb shell dumpsys media.audio_flinger
adb bugreport bugreport-leaudio
```

不同产品的 dumpsys 分段和字段会发生变化。Android 17 AOSP 的 `LeAudioService.dump()` 会输出 active group、活跃输入/输出设备、组和设备状态，以及内部事件记录。应先在完整输出或 bugreport 中搜索 `LeAudioService`、`Active Groups`、`BLE_HEADSET`、`BLE_SPEAKER` 和 `BLE_BROADCAST`，不要依赖某一行的固定格式。

建议同时记录：

- build fingerprint（系统构建的唯一标识）、Android API、Bluetooth Mainline（可独立更新的蓝牙系统模块）版本；
- 手机与耳机固件；
- 当前 active 设备与音频模式；
- group ID、左右设备、输入/输出方向；
- Codec、frame duration、octets/frame、Presentation Delay；
- software/offload session；
- 流启动前后的 monotonic clock（不受系统时间校准影响的单调时钟）时间点。

### 第二步：用 HCI snoop 还原控制过程

先通过开发者选项启用 Bluetooth HCI snoop log（HCI 数据包记录），再采集 bugreport。日志文件位置和直接读取权限会随构建变化，优先从 bugreport 提取，避免在脚本中硬编码 `/data/misc/...` 私有路径。

在 Wireshark 或厂商分析器中按事件顺序检查：

- PACS/ASCS 的 GATT 读写与通知；
- `LE Set CIG Parameters`；
- `LE Create CIS` / `LE CIS Request` / CIS established；
- ISO data path 配置；
- ISO 数据包的 handle（连接标识）、方向、序号和丢失情况；
- CIG/BIG 释放；
- 广播公告、周期广播同步与 BIG 同步。

Wireshark 字段名会随 dissector（协议解析器）版本变化。`btatt` 常用于 ATT/GATT，ISO 过滤字段应以当前版本能够识别的协议树为准，不要把某个固定过滤字符串写进自动化判据。

### 第三步：用 Perfetto 看 Host 侧

Perfetto 适合检查 AudioFlinger 线程、Binder、调度、CPU idle/frequency 和 wakeup；HCI snoop 更适合还原空口控制过程与 ISO 数据包。AOSP 不保证 Android 17 提供名为 `android.bluetooth` 的专用 Perfetto data source（数据源），也不能假定所有产品都有 `btif_le_audio_thread` 这条固定轨道。

采集前应先查询目标系统构建支持的数据源与 atrace categories（可跟踪类别），再选择：

- `audio` / AudioFlinger；
- `sched`、线程状态和 wakeup；
- Binder driver；
- CPU frequency/idle 和电源轨；
- vendor 提供且已确认存在的 Bluetooth trace。

把 trace 中的 Host 时间点与 btsnoop 中的 HCI 时间点对齐，才能区分应用供数慢、Audio HAL 缓冲、Bluetooth 建流慢和射频异常。

### 第四步：用声学标记测端到端

稳态单向延迟最好使用已知波形：

1. 在源端生成脉冲、MLS（最大长度序列）或带时间标记的音频；
2. 用外部声卡或同步采集设备记录源参考与耳机声学输出；
3. 对多次事件做互相关，用波形相似度估算时间偏移，并报告中位数、P95/P99（第 95/99 百分位）和离群值；
4. 另行统计冷启动、已连接启动和路由切换间隙；
5. 同步保存 Codec/QoS、HCI snoop、Perfetto 和射频条件。

仅凭 logcat 中的“stream started”无法得到声学端到端延迟，因为该日志时间点通常位于控制面；之后还要经过 Presentation Delay、耳机缓冲和声学渲染。

## 常见误判

| 误判 | Android 17 下更准确的结论 |
|---|---|
| LE Audio 会取代所有 Classic Audio | 两种传输长期共存，双模设备仍常见 |
| 7.5 ms LC3 帧意味着 7.5 ms 算法或端到端延迟 | 帧时长只是预算中的一项 |
| LE Audio 单向延迟固定为 20–40 ms | 延迟由两端缓冲、QoS、Presentation Delay 和实现共同决定 |
| LC3 CPU 占用一定低于 SBC | 执行位置、实现与配置不明确时无法比较 |
| 有 DSP 就不会唤醒 AP | 要确认当前 session 和数据路径已经 offload |
| 多流天然更省手机电量 | 多流减少某些耳间中继，也增加手机侧流和空口调度 |
| 广播丢包会立即形成一次可闻断音 | 还受重复、交织、丢包隐藏和缓冲影响 |
| `AUDIO_DEVICE_OUT_DEFAULT` 表示 LE 广播 | Android 17 定义了独立的 `AUDIO_DEVICE_OUT_BLE_BROADCAST` |
| `setBluetoothScoOn()` 可切换 Auracast | SCO 属于 HFP/Classic，且该 API 已弃用 |
| ASHA 是 Classic 助听协议 | ASHA 使用 BLE L2CAP CoC；HAP 才是标准 LE Audio/GAF 路径 |
| LE Audio 连接会阻止设备进入 Deep Doze | 是否 suspend/idle 要看活跃音频、wakeup 和系统电源状态 |
| 10 ms 帧会让 AP 固定每秒唤醒 100 次 | Controller、批处理与 offload 可以改变 Host 唤醒节奏 |
| Perfetto 固定提供 `android.bluetooth` 数据源 | 先查询目标构建；AOSP 不保证该专用数据源 |

## 代码审阅清单

面向应用：

- 能力检查按 `BluetoothStatusCodes` 处理错误码；
- 通信路由使用 `setCommunicationDevice()`，结束时清理偏好；
- 不通过 SCO API 控制 LE Audio；
- 监听设备与路由变化，避免缓存设备类型；
- 把冷启动、稳态延迟和切换间隙分开统计；
- 不把耳机品牌的 Gaming Mode 当成 7.5 ms 或某个延迟承诺。

面向系统与设备实现：

- PACS 声明与 Codec/QoS 选择一致；
- ASCS 状态、CIG/CIS 生命周期和 Audio HAL session 对得上；
- software/offload 路径可以通过 dump、trace 或 vendor telemetry（厂商遥测数据）确认；
- Presentation Delay 与左右同步满足产品目标；
- 干扰条件下同时评估丢包、glitch、功耗和延迟；
- 广播测试覆盖扫描、PA（周期广播）/BIG 同步、加密与多 BIS；
- HAP 和 ASHA 使用各自正确的数据路径与麦克风假设。

## 参考资料

- [Android Bluetooth Low Energy Audio overview](https://developer.android.com/develop/connectivity/bluetooth/ble-audio/overview)：Android 13 支持、双模设备、使用场景、能力检查和应用路由 API。
- [AOSP Bluetooth architecture](https://source.android.com/docs/core/connect/bluetooth)：Framework、Binder、Bluetooth 进程、JNI、Native stack 与 vendor 实现边界。
- [Bluetooth SIG: Introducing Bluetooth LE Audio](https://www.bluetooth.com/wp-content/uploads/2022/01/Introducing-Bluetooth-LE-Audio-book.pdf)：GAF、BAP、CIS/BIS、ASCS、LC3 与广播过程。
- [AOSP ASHA](https://source.android.com/docs/core/connect/bluetooth/asha)：BLE L2CAP CoC、弹性缓冲、左右助听器拓扑和无 backlink 约束。
- [BluetoothAdapter.java（android-17.0.0_r1）](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:packages/modules/Bluetooth/framework/java/android/bluetooth/BluetoothAdapter.java)：LE Audio 与广播源能力状态码。
- [BluetoothLeAudio.java（android-17.0.0_r1）](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:packages/modules/Bluetooth/framework/java/android/bluetooth/BluetoothLeAudio.java)：Profile proxy、公开查询接口和受限控制接口。
- [LeAudioService.java（android-17.0.0_r1）](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:packages/modules/Bluetooth/android/app/src/com/android/bluetooth/le_audio/LeAudioService.java)：组、活跃设备、广播/单播状态与 dump。
- [LE Audio Native stack（android-17.0.0_r1）](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:packages/modules/Bluetooth/system/bta/le_audio/)：Codec、ASE、CIG/CIS、广播与状态机实现。
- [SessionType.aidl（android-17.0.0_r1）](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:hardware/interfaces/bluetooth/audio/aidl/android/hardware/bluetooth/audio/SessionType.aidl)：单播、广播、软件与 offload 数据路径。
- [audio-base-utils.h（android-17.0.0_r1）](https://cs.android.com/android/platform/superproject/+/android-17.0.0_r1:system/media/audio/include/system/audio-base-utils.h)：BLE headset、speaker、broadcast、hearing aid 与 central 设备类型。
- [Audio Managed SCO rearchitecture](https://source.android.com/docs/core/audio/sco-audio-mgmt)：Android 17 的 SCO/HFP 边界，用于避免把 SCO 改动误写成 LE Audio 改动。
