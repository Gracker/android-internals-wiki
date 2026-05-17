---
title: "Bluetooth 扫描与连接功耗分析"
chapter: "11.6"
section: "11.6"
status: draft
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
tags: [bluetooth, ble, power, batterystats, connectivity, app-standby]
related_chapters: ["11.1", "11.2", "11.5", "19.25", "25.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-17"
gap_source: "AOSP结构+官方文档+每日信息"
sources:
  - type: official
    path: "https://developer.android.com/develop/connectivity/bluetooth/ble/find-ble-devices"
  - type: official
    path: "https://developer.android.com/develop/connectivity/bluetooth/ble/background"
  - type: official
    path: "https://developer.android.com/develop/connectivity/bluetooth/bt-permissions"
  - type: official
    path: "https://source.android.com/docs/core/connect/bluetooth"
  - type: official
    path: "https://source.android.com/docs/core/power/values"
  - type: aosp
    path: "packages/modules/Bluetooth"
  - type: aosp
    path: "packages/apps/Bluetooth/src/com/android/bluetooth/gatt/ScanManager.java"
---

# 11.6 Bluetooth 扫描与连接功耗分析

<!-- outline-start -->
## 要点

### 🔹 Bluetooth 功耗问题的分类
区分经典 Bluetooth 连接、BLE 扫描、BLE 广播、GATT 连接保持和音频链路。正文需要说明每类活动对应的耗电路径、归因入口和常见误判。

### 🔹 BLE 扫描的电量成本
覆盖扫描窗口、扫描模式、过滤条件、结果回调频率和批量扫描。重点解释为什么无过滤、长时间、前台页面退出后仍运行的扫描会放大功耗。

### 🔹 后台扫描与系统限制
梳理 Android 8.0 之后后台执行限制、Android 12+ Bluetooth 权限拆分、`BLUETOOTH_SCAN` 与位置权限边界，以及 `PendingIntent` 扫描在后台场景中的适用条件。

### 🔹 AOSP Bluetooth 栈的归因路径
从 `BluetoothLeScanner.startScan()` 进入 Bluetooth 进程，定位 `ScanManager`、`AppScanStats`、扫描超时和扫描滥用保护。正文需要把 App 发起方、系统服务和 controller 统计的边界讲清楚。

### 🔹 诊断入口：dumpsys、batterystats 与 Perfetto
整理 `dumpsys bluetooth_manager`、`dumpsys batterystats`、Battery Historian、Perfetto power rails / wakelock / Bluetooth 事件的组合用法。每个入口需要说明能回答什么问题，不能回答什么问题。

### 🔹 治理策略
覆盖短周期按需扫描、明确过滤条件、页面生命周期绑定、连接复用、失败退避、扫描结果缓存、前台服务边界和隐私脱敏。策略要落到 App 代码可执行动作。

## 扩展

### 🔸 BLE Audio 与空间音频功耗
结合 8.8 多媒体管线和 11.1 功耗模型，补充 BLE Audio、头动追踪和音频渲染链路的功耗观察点。

### 🔸 Companion Device Manager 替代长轮询扫描
评估 Companion Device Manager 在穿戴、配件、IoT 场景中替代自维护扫描循环的条件。

### 🔸 厂商 ROM 的 Bluetooth 扫描限制差异
记录 OEM 对后台扫描、扫描频率和白名单策略的差异，缺实机数据时标注待验证。

<!-- outline-end -->

> 本节内容待加工。
