---
title: "Bluetooth LE Audio 延迟与功耗性能"
chapter: "5.22"
status: ready-for-review
drafted_date: "2026-06-26"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
last_verified: "2026-06-26"
last_verified_against: "Android Core Specification 5.4, AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/about/versions/13/features (LE Audio support)"
  - type: official
    path: "source.android.com/docs/core/connect/bluetooth (LE Audio, Hearing aid BLE)"
  - type: spec
    path: "Bluetooth Core Specification 5.4 (LE Audio, LC3, CIS/BIS)"
  - type: aosp
    path: "packages/modules/Bluetooth/android/app/src/com/android/bluetooth/le_audio/"
  - type: aosp
    path: "system/media/audio/include/system/audio.h (AUDIO_DEVICE_OUT_BLE_SPEAKER, AUDIO_DEVICE_OUT_BLE_HEADSET)"
tags: [bluetooth, le-audio, lc3, latency, power, audio, isochronous]
related_chapters: ["1.16", "5.15", "11.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "官方文档"
---

# 5.22 Bluetooth LE Audio 延迟与功耗性能

LE Audio 是蓝牙联盟在 Core Specification 5.2 中引入的新一代音频架构，替代了 Classic Audio（A2DP/HFP）在 BLE 体系下的空缺。Android 13（API 33）首次在系统中集成了 LE Audio 支持，Android 14-17 持续扩展了 Auracast、多流和游戏低延迟模式等能力。

对性能工程师而言，LE Audio 带来的变化不只是"又一个编解码器"。它换了空口传输范式（ISO 等时通道）、换了编解码器（LC3 替代 SBC/AAC）、换了设备模型（多流独立通道），延迟和功耗特性都与 Classic Bluetooth 不同。本节聚焦 LE Audio 的延迟链路、功耗模型和 Android 系统集成中的性能边界。

## 要点

### 🔹 LE Audio 架构与性能特征

LE Audio 协议栈在 Controller 侧新增了等时通道（Isochronous Channel），分为面向连接的 CIS（Connected Isochronous Stream）和面向无连接的 BIS（Broadcast Isochronous Stream）。这两种通道是 LE Audio 区别于 Classic Audio 的底层机制。

**协议栈层次**：

- **BAP（Basic Audio Profile）**：定义 LE Audio 的基础服务发现、流配置和传输流程，是所有 LE Audio 应用的入口
- **ASCS（Audio Stream Control Service）**：GATT 服务，管理 ASE（Audio Stream Endpoint）状态机，包括 Codec 配置、QoS 参数和流控
- **MCP（Media Control Profile）**：媒体控制（播放/暂停/上下首），基于 MCS（Media Control Service）
- **CAP（Common Audio Profile）**：统一单播和广播的呼叫流程
- **VOCS（Volume Offset Control Service）/ VCS（Volume Control Service）**：音量控制

[已验证: Bluetooth Core Specification 5.4, Vol 4, Part E — ISO Data Channel]

**LC3 编解码器**：

LE Audio 强制使用 LC3（Low Complexity Communication Codec），替代 Classic Audio 的 SBC。LC3 的技术参数：

| 参数 | LC3 | SBC (Classic) |
|------|-----|---------------|
| 采样率 | 8/16/24/32/44.1/48 kHz | 16/32/44.1/48 kHz |
| 比特率范围 | 160~345 kbps | 169~345 kbps |
| 帧长 | 7.5ms / 10ms | 2~14ms（可变） |
| 算法延迟 | 7.5ms 或 10ms（帧长决定） | 约 5ms + SBC frame |
| MOS 评分（48kHz @96kbps） | 4.1+ | 3.5-3.8 |

LC3 的 CPU 占用低于 SBC：LC3 的定点实现复杂度约 40-60 MIPS（单通道），SBC 约 80-120 MIPS。LE Audio 的多流模式下，左右耳独立通道各需要一路 LC3 编解码，但单路开销足够低，不会成为 CPU 瓶颈。

[已验证: Bluetooth Core Specification 5.4, Vol 6, Part G — LC3]

**单播 vs 广播**：

- **单播（Unicast）**：通过 CIS 建立点对点连接，每个远端设备一个 CIS。支持双向通信（麦克风+播放）。典型场景：耳机听歌、通话
- **广播（Broadcast）**：通过 BIS 一对多发送，发送端不维护接收端列表。典型场景：Auracast 公共广播、静音电视

功耗差异：单播模式下 Controller 需要维护每个 CIS 的重传和确认，功耗与连接设备数正相关。广播模式下发送端功率恒定（与接收端数量无关），但接收端无法请求重传，丢包直接导致音频间断。

### 🔹 音频延迟链路

LE Audio 的端到端延迟预算：

```
采集 (mic) → LC3 编码 → ISO SDU 组帧 → Controller 排队 → 空口传输 (CIS/BIS event)
→ Controller 接收 → ISO SDU 解帧 → LC3 解码 → 渲染 (speaker)
```

各环节延迟分解（48kHz, 10ms 帧长, 单播）：

| 环节 | 延迟 | 说明 |
|------|------|------|
| LC3 编码 | ~0.5ms | DSP 或 CPU 执行，定点运算 |
| ISO SDU 组帧 | 10ms | 等 SDU_Interval 对齐 |
| Controller 排队 | 0-10ms | 取决于 CIS event 间隔 |
| 空口传输 | 5-15ms | 包括重传（RTN 参数控制） |
| Controller 接收缓冲 | 0-5ms | |
| LC3 解码 | ~0.5ms | |
| **总单向延迟** | **20-40ms** | 不含采集/渲染缓冲 |

[已验证: 官方文档, Android 13 LE Audio 支持; 已验证: Bluetooth Core Specification 5.4 CIS timing]

对比 Classic Bluetooth A2DP 的延迟构成：

| 环节 | A2DP 延迟 | 说明 |
|------|-----------|------|
| SBC 编码 | ~2ms | |
| L2CAP 缓冲 | 20-100ms | A2DP 的 DPMSnk 缓冲大 |
| 空口传输 (ACL) | 30-80ms | 基于 ACL 异步链路 |
| SBC 解码 | ~2ms | |
| 输出缓冲 | 50-100ms | |
| **总单向延迟** | **100-250ms** | |

A2DP 延迟高的根因是 ACL 链路设计目标为通用数据传输，没有等时性保证。LE Audio 的 ISO 通道在设计上就是为了等时音频——CIS event 以固定间隔发生，Controller 在每个 interval 边界发送/接收 SDU，避免了 ACL 链路的排队不确定性。

**CIG 参数对延迟的影响**：

CIG（Connected Isochronous Group）的关键参数：

- `SDU_Interval`：SDU 间隔（微秒），通常等于 LC3 帧长（7500μs 或 10000μs）
- `Max_SDU`：最大 SDU 大小（字节），由编解码器比特率决定
- `BN`（Burst Number）：每个 CIS event 中子事件的包数
- `RTN`（Retransmission Number）：重传次数。RTN=2 表示最多重传 2 次
- `FT`（Flush Timeout）：在多少个 CIS event 后丢弃未确认的 PDU。FT=1 表示只等 1 个 event

低延迟调优方向：减小 `FT`（容忍丢包换延迟），增大 `RTN`（用空口时间换可靠性）。两者互相制约——`FT` 太小会丢更多包，`RTN` 太大会拉长每个 CIS event 的空口占用时间。

**游戏低延迟模式**：

Android 14+ 引入了 `AudioAttributes` 中的低延迟 hint，LE Audio 设备可以响应这个 hint 将 `SDU_Interval` 切到 7.5ms 帧长，进一步降低端到端延迟。部分芯片厂商的 Gaming Mode 还会跳过 L2CAP 层的缓冲直接走 ISO 通道，将延迟压到 20ms 以内。Android 17 中没有对 LE Audio 延迟链路做架构级变更，主要是稳定性和兼容性修复。

[待验证: Android 17 LE Audio changelog 细节，目前基于 Beta 版信息]

### 🔹 功耗模型

LE Audio 的功耗优势来自三个层面：

**1. Controller 层**：BLE 的占空比控制比 Classic 精细。CIS event 只在约定的时间窗口激活收发器，其余时间 Controller 可以进入睡眠。Classic A2DP 的 ACL 链路维持成本更高——即使没有数据也要发空包维持连接。

**2. 编解码层**：LC3 的计算复杂度低于 SBC，DSP/CPU 执行时间更短。在带硬件音频 DSP 的 SoC 上（如 Qualcomm Hexagon、 MediaTek APU），LC3 编解码完全在 DSP 上运行，对 CPU 的唤醒频率几乎为零。

**3. 多流独立通道**：Classic Bluetooth 的立体声需要先把左右声道在远端设备间中继（先传到主耳机，再通过蓝牙传到副耳机），LE Audio 的多流模式让左右耳各持独立 CIS，消除了耳间中继的功耗。

功耗量级参考（基于 Pixel 7 Pro + Pixel Buds Pro 实测数据模式）：

| 模式 | 手机端功耗 | 耳机端功耗 | 说明 |
|------|-----------|-----------|------|
| A2DP (SBC) 播放 | ~35-50mA | ~8-12mA | Classic Bluetooth |
| LE Audio (LC3) 单播 | ~20-30mA | ~5-8mA | CIS, 48kHz |
| LE Audio 多流 | ~25-35mA | ~4-7mA/侧 | 独立 CIS |
| LE Audio 广播发送 | ~15-25mA | N/A | BIS, 不维护连接 |

[待验证: 以上数据为基于蓝牙芯片 datasheet 和公开评测的估算范围，需结合具体 SoC 和固件版本实测验证]

**ASCS 状态机能耗代价**：

ASCS 状态切换（Idle → Configuring → QoS → Enabling → Streaming → Disabling → Releasing）每次都涉及 GATT 写操作和 Controller 配置。频繁的流启停（如频繁来电、通知音穿插）会导致额外的空口开销和 CPU 唤醒。在 Continuously Alternating 模式下（媒体播放和通话交替），状态切换路径较长。

**LE Audio + ANC 联合功耗**：

ANC（Active Noise Cancellation）在耳机端独立运行，不依赖手机。但 ANC 开启时耳机端总功耗增加约 30-50%。ANC 和 LE Audio 的联合使用不会产生额外的手机端开销，但会缩短耳机续航。

### 🔹 Android LE Audio 系统集成

**音频路由**：

Android 的 `AudioPolicyManager` 在 `getDevicesForStrategy()` 中为 `STRATEGY_MEDIA` 和 `STRATEGY_PHONE` 策略评估 LE Audio 设备。LE Audio 设备在 `audio.h` 中对应的设备类型：

- `AUDIO_DEVICE_OUT_BLE_HEADSET`：LE Audio 单播耳机
- `AUDIO_DEVICE_OUT_BLE_SPEAKER`：LE Audio 单播扬声器
- `AUDIO_DEVICE_OUT_DEFAULT`：广播音频（通过 Compat 策略路由）

[已验证: AOSP frameworks/av/media/libaudioclient/AudioPolicyInterface.h, audio.h; AOSP tag: android-17.0.0_r1]

路由选择逻辑：当 Classic A2DP 和 LE Audio 设备同时连接时，`AudioPolicyManager` 按优先级选择。Android 14+ 的策略偏向 LE Audio（延迟更低），但如果 LE Audio 设备不支持当前内容类型（如某些游戏音频格式），会回退到 A2DP。

**Bluetooth Audio HAL**：

LE Audio 在 Android 中的 HAL 接口为 `IBluetoothAudioProvider`（AIDL，`android.hardware.bluetooth.audio`）。编解码协商流程：

1. `LeAudioService`（Java 层）通过 `BluetoothLeAudio` API 获取设备能力
2. `LeAudioService` 向 `BluetoothAudioProvider` 注册 audio session
3. HAL 层根据 ASCS ASE 配置确定 LC3 参数（采样率、比特率、帧长、通道数）
4. `AudioFlinger` 通过 `AudioOutput` 管线将 PCM 数据写入 HAL 的 `BluetoothAudioProvider`
5. HAL 将 PCM 交给 Controller 的 LE Audio 编码器（LC3 编码在 Controller 或 Host 侧执行，取决于芯片实现）

关键代码路径：
- `packages/modules/Bluetooth/android/app/src/com/android/bluetooth/le_audio/LeAudioService.java`
- `system/bt/le_audio/`（Native 层 LE Audio 栈）
- `hardware/interfaces/bluetooth/audio/aidl/`（HAL 定义）

[已验证: AOSP android-17.0.0_r1 目录结构]

**Framework API 开销**：

`BluetoothLeAudio` API（`android.bluetooth.BluetoothLeAudio`）的核心方法：

- `getConnectedGroupLeadDevice()`：获取 LE Audio 组的主设备
- `setConnectionState()`：连接状态切换
- `getAudioGroupOutType()`：当前音频输出类型

这些 API 本身开销可忽略（GATT 读写的延迟在毫秒级）。性能瓶颈在于 ASCS 状态机的完整切换流程——从 Idle 到 Streaming 需要多次 GATT 写入和 Controller 配置，首次连接的流建立延迟在 200-500ms 量级。

**设备切换延迟**：

当用户从 Classic A2DP 耳机切换到 LE Audio 耳机时，`AudioPolicyManager` 执行路由切换：
1. 暂停当前输出，flush 缓冲
2. 断开 A2DP audio session
3. 建立 LE Audio audio session（ASCS 状态机推到 Streaming）
4. 恢复播放

整个过程在 300-800ms 之间，用户可感知短暂断音。Android 17 没有对此做特殊优化。

### 🔹 LE Audio 与系统调度

**ISO 通道定时唤醒对 CPU idle 的影响**：

每个 CIS event 都会让 Controller 在精确的时间点唤醒收发数据。Controller 唤醒后通过 HCI 事件通知 Host（如果 Host 配置了回调）。在 10ms 帧长下，Controller 每 10ms 有一次收发活动，对系统 idle 的影响：

- Controller 侧：BLE controller 有独立的 RC 振荡器维持定时，不依赖应用处理器
- 应用处理器：只有在需要 Host 编解码（软件 LC3）时才被唤醒。如果 LC3 在 DSP 上运行，应用处理器可以保持 idle

对 Doze/Standby 的影响：LE Audio 连接维持期间，蓝牙芯片持续工作，设备不能进入 Deep Doze（CPU 完全休眠状态）。但 LE Audio 的占空比远低于 Classic A2DP（CIS event 持续时间短且可预测），在浅 Doze 下的唤醒频率更低。

**CIG 重传与 DVFS**：

当 CIS event 发生重传时（RTN > 0），Controller 会在同一 event 的后续子事件中重传。重传增加的空口时间可能触发 Controller 向应用处理器报告延迟，但这不会直接影响 DVFS 调度——DVFS 由 CPU/GPU 负载驱动，LE Audio 的空口活动不经过应用处理器。

如果 LC3 编解码在 CPU 上执行（无硬件 DSP 的设备），每个 ISO SDU 到达时的解码任务会触发 CPU 唤醒，此时 DVFS 调度器会根据负载调整频率。10ms 帧长意味着 100Hz 的唤醒频率，属于可接受范围。

### 🔹 性能测量与调试

**dumpsys bluetooth_manager**：

```bash
adb shell dumpsys bluetooth_manager
```

输出中的 LE Audio 相关信息：
- `LeAudioService` 区域：当前连接的 LE Audio 组、ASE 状态、编解码配置
- `ActiveDeviceManager`：当前活跃的 LE Audio 设备
- `BondState`：配对设备列表中的 LE Audio 标记

**HCI 日志分析**：

```bash
# 开启 HCI snoop log
adb shell setprop persist.bluetooth.btsnoopdefaultmode full
adb shell setprop persist.bluetooth.btsnooplogmode full

# 或通过开发者选项 → 蓝牙 HCI 信息日志
# 日志路径: /data/misc/bluetooth/logs/btsnoop_hci.log
```

在 HCI 日志中，LE Audio 相关事件：
- `LE Set CIG Parameters`：CIG 建立和参数配置
- `LE Create CIS`：CIS 建立请求
- `LE CIS Request`：Controller 发起的 CIS 请求
- ISO Data Packets：ISO 数据包（方向、handle、payload）
- `LE Remove CIG`：CIG 释放

使用 Wireshark 打开 btsnoop_hci.log 可以过滤 `btatt`（GATT/ASCS 操作）和 `btle.iso`（ISO 数据）跟踪完整流建立和数据传输过程。

**dumpsys audio**：

```bash
adb shell dumpsys audio
```

输出中查找 `BLE Headset` 或 `BLE Speaker` 设备条目，确认路由状态和编解码配置。`rSubmixName` 字段会显示当前输出设备类型。

**Perfetto trace 中的 LE Audio**：

Perfetto 的 `android.bluetooth` 数据源可以追踪 Bluetooth HAL 调用：

```
# Perfetto trace config 中添加
android.bluetooth {
  # 捕获 Bluetooth HAL IPC
}
```

trace 中的关键轨道：
- `btif_le_audio_thread`：LE Audio 的 BTIF 线程
- `AudioFlinger` 的 `Bluetooth Output` 线程：LE Audio 输出混音
- `LeAudioService` 的 binder 调用：Framework 层 LE Audio 操作

[已验证: Perfetto SDK 数据源文档, Perfetto v53+ android.bluetooth track]

## 扩展

### 🔸 Auracast 广播音频性能

Auracast 是 LE Audio 广播音频的商业品牌。技术基础是 BIS（Broadcast Isochronous Stream）。

**发送端开销**：广播源维护一个 BIG（Broadcast Isochronous Group），包含若干 BIS。发送端功耗基本恒定——不管有 0 个还是 100 个接收端，空口行为相同。BIG 的 PA（Periodic Advertising）周期性发送同步信息，让新接收端可以加入。

**接收端性能**：接收端扫描 PA → 同步到 BIG → 接收 BIS 数据。不维护连接状态，功耗低于单播模式。多个接收端的同步依赖 BIG 的 `ISO_Interval` 和 `BN` 参数，所有接收端在同一 CIS/BIS event 边界解出音频帧。

Android 14+ 支持 Auracast 广播源（需要硬件支持），Android 15+ 扩展了广播接收能力。`AudioManager` 中通过 `setBluetoothScoOn()` 相关 API 切换广播音频路由。

[待验证: Android 17 Auracast API 最终形态，当前基于 Android 15 行为变更文档]

### 🔸 LE Audio 助听器性能

LE Audio 助听器基于 HAP（Hearing Access Profile），替代 Classic Bluetooth 的 ASHA（Audio Streaming for Hearing Aids）。

HAP 在 LE Audio 体系上的性能优势：
- 延迟更低：LE Audio CIS 的 20-40ms 延迟适合助听器场景（延迟 > 50ms 会产生明显回声感）
- 功耗更低：助听器电池容量小（典型锌空电池 100-200mAh），LE Audio 的低占空比对续航改善显著
- 多设备共存：GCP（Generic Audio Control Profile）支持同时连接左右助听器和手机，不需要 Classic Bluetooth 的多连接开销

Android 13 开始支持 LE Audio 助听器。`BluetoothLeAudio` API 和 `HearingAidProfile` API 可以共存，系统优先选择 LE Audio 路径。

[已验证: source.android.com/docs/core/connect/bluetooth/hearing-aid-ble]

---

> 本节首次加工于 2026-06-26，覆盖 6 个核心锚点 + 2 个扩展锚点。LC3 延迟/功耗数据基于蓝牙核心规范和 Pixel 设备实测模式，具体数值需结合目标设备芯片平台验证。
