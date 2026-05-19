---
title: "SensorService 与传感器批处理功耗模型"
chapter: "5.15"
status: draft
applicable_versions: "Android 4.4 (API 19) - Android 17 (API 37)"
tags: [sensorservice, sensors, power, batching, cpu-wakeup]
related_chapters: ["5.6", "11.2", "25.5", "14.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "AOSP结构/官方文档"
source_candidates:
  - "https://cs.android.com/android/platform/superproject/+/master:frameworks/native/services/sensorservice/"
  - "https://cs.android.com/android/platform/superproject/+/master:frameworks/base/services/core/java/com/android/server/sensors/"
  - "https://developer.android.com/develop/sensors-and-location/sensors/sensors_overview"
  - "https://developer.android.com/reference/android/hardware/SensorManager"
  - "https://developer.android.com/blog/posts/battery-technical-quality-enforcement-is-here-how-to-optimize-common-wake-lock-use-cases"
---

# 5.15 SensorService 与传感器批处理功耗模型

<!-- outline-start -->
## 要点

### 🔹 传感器耗电的三类成本
区分传感器本体采样、sensor hub / HAL 缓冲、应用处理器被唤醒后处理事件三类成本，避免把“采样频率低”直接等同于“省电”。

### 🔹 SensorService 在系统功耗路径里的位置
梳理 App `SensorManager`、framework sensors service、native `SensorService`、Sensor HAL 和硬件 FIFO 的分工，说明系统如何把多个客户端的采样需求合并给底层。

### 🔹 `samplingPeriodUs` 与 `maxReportLatencyUs`
解释采样周期和最大上报延迟的不同含义：前者控制数据产生频率，后者控制批量交付窗口；批处理收益来自减少 AP 唤醒次数，不来自减少传感器采样本身。

### 🔹 wake-up / non-wake-up sensor 与 sensor hub
说明 wake-up sensor、non-wake-up sensor、significant motion、step counter 等类型对 suspend、唤醒和事件交付的影响，并标出不同设备硬件能力差异。

### 🔹 批处理失效的常见原因
覆盖硬件 FIFO 不足、多个客户端请求高频低延迟、前后台生命周期未退订、监听器泄漏、厂商 HAL 限制等导致批处理窗口被打断的情况。

### 🔹 Perfetto、Battery Historian 与 `dumpsys sensorservice` 观察点
给出后续正文需要验证的证据入口：sensor event 频率、wake lock、AP wakeup、CPU freq、battery stats、`dumpsys sensorservice` active connections 与 batching 状态。

### 🔹 与 App 层传感器治理的边界
本节负责系统路径和功耗模型，25.5 节负责 App 侧 API 选择、生命周期退订和业务降级；正文只做交叉引用，不重复写实战策略。

## 扩展

### 🔸 Sensor Direct Channel 与高频传感器流
后续可补充 API 26+ direct channel 在高频传感器数据通路中的适用边界，以及它与普通事件回调的功耗差异。

### 🔸 OEM sensor hub 策略差异
后续可收集 Pixel、Qualcomm、MediaTek 设备上的 FIFO 深度、wake-up sensor 支持和厂商 HAL 日志差异。

### 🔸 与定位、蓝牙和后台任务的功耗归因协同
后续可把传感器批处理与 FLP、BLE scan、JobScheduler/WorkManager 放在同一条电量归因时间线上。

<!-- outline-end -->

> 本节内容待加工。
