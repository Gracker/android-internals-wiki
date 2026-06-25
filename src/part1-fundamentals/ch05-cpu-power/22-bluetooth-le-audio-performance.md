---
title: "Bluetooth LE Audio 延迟与功耗性能"
chapter: "5.22"
status: draft
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
tags: [bluetooth, le-audio, lc3, latency, power, audio]
related_chapters: ["1.16", "5.15", "11.6"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-26"
gap_source: "官方文档"
---

# 5.22 Bluetooth LE Audio 延迟与功耗性能

<!-- outline-start -->
## 要点

### 🔹 LE Audio 架构与性能特征
- LE Audio 协议栈（BAP/CAP/ASCS/MCP）的系统开销概览
- LC3 编解码器 vs SBC/AAC 的 CPU 占用与音质对比
- LE Audio Isochronous 通道的调度机制与延迟特性
- 单播（Unicast）与广播（Broadcast）模式的功耗差异

### 🔹 音频延迟链路
- LE Audio 端到端延迟预算：采集 → LC3 编码 → ISO 传输 → LC3 解码 → 渲染
- Classic Bluetooth A2DP 延迟（100-200ms）vs LE Audio 延迟（20-40ms）的系统级原因
- 连接等间隔（CIG）参数对延迟的影响：`SDU_Interval`/`Max_SDU`/`RTN` 的调优
- 游戏/通话场景的低延迟模式（Gaming Mode / Low Latency Mode）

### 🔹 功耗模型
- LE Audio 连接状态功耗 vs Classic A2DP 劏耗
- 多流（Multi-Stream）模式下的功耗增量
- ASCS（Audio Stream Control Service）状态机切换的能耗代价
- LE Audio + ANC 主动降噪的联合功耗

### 🔹 Android LE Audio 系统集成
- `AudioPolicyManager`/`AudioFlinger` 对 LE Audio 设备的路由选择逻辑
- `BluetoothAudioSoa` / `LeAudioSoa` HAL 接口与编解码协商
- `BluetoothLeAudio` Framework API 的调用开销
- `AudioManager.getDevices(LE_AUDIO)` 与设备切换延迟

### 🔹 LE Audio 与系统调度
- ISO 通道的定时唤醒对 CPU idle 的影响
- `CIG` 重传策略与 DVFS 调度的交互
- LE Audio 连接维持对 Doze/Standby 模式的影响

### 🔹 性能测量与调试
- `dumpsys bluetooth_manager` 中 LE Audio 会话统计
- `btsnoop_hci` 日志中 ISO 数据包延迟分析
- `adb shell dumpsys audio` 中 LE Audio 路由信息
- HCI 厂商日志在 LE Audio 延迟归因中的使用

## 扩展

### 🔹 Auracast 广播音频性能
- 广播源（Broadcast Source）的 CPU 与内存开销
- 广播音频同步（BigSync）的延迟特性
- 多个广播接收端的资源消耗

### 🔸 LE Audio 助听器（Hearing Aid）性能
- HAP（Hearing Access Profile）对系统资源的需求
- LE Audio 助听器与 Classic ASHA 的功耗对比

<!-- outline-end -->

> 本节内容待加工。
