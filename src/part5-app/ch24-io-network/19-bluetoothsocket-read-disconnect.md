---
title: "BluetoothSocket read 断开语义与长连接治理"
chapter: "24.19"
section: "24.19"
status: draft
applicable_versions: "Android 5 (API 21) - Android 17 (API 37)"
tags: [bluetooth, io, network, android17, long-connection]
related_chapters: ["11.6", "12.2", "24.4", "24.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-25"
gap_source: "官方文档/Android17行为变更/Part5结构参考"
gap_score: 18
material_count: 4
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/develop/connectivity/bluetooth/transfer-data"
  - type: official
    path: "https://developer.android.com/reference/android/bluetooth/BluetoothSocket"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - CPU 优化（上）：合理使用线程池，提升 CPU 利用率.md]"
  - type: clippings-structure
    path: "[结构参考: Clippings/Android 性能优化 - 任务调度优化：线程+CPU，提升任务调度优先级.md]"
---

# 24.19 BluetoothSocket read 断开语义与长连接治理

<!-- outline-start -->
## 要点

### 🔹 Android 17 RFCOMM `read()` 返回值变化
梳理 Android 17 面向 `targetSdkVersion >= 37` 的 Bluetooth RFCOMM socket 行为：远端断开或 socket 关闭时，`InputStream.read()` 可返回 `-1`，应用不能只依赖 `IOException` 退出读循环。

### 🔹 读写线程模型与阻塞边界
结合官方 Bluetooth 数据传输文档，说明 `read(byte[])` 和 `write(byte[])` 都可能阻塞，读循环需要专用线程、明确退出条件和可观测状态，不把阻塞等待放进主线程或 UI 回调。

### 🔹 断线归因与状态机
区分主动关闭、远端断开、链路丢失、权限撤销、蓝牙关闭和协议层心跳超时，把 `-1`、`IOException`、业务超时和用户操作分别映射到状态机事件。

### 🔹 长连接重连与退避策略
设计重连预算、指数退避、用户可见状态、前后台切换策略和设备重发现边界，避免断线后立即高频扫描或无限重连。

### 🔹 性能与功耗监控字段
给出连接时长、读循环退出原因、重连次数、扫描时长、线程存活、写入阻塞耗时和蓝牙功耗归因字段，和 11.6 的蓝牙扫描功耗章节建立引用关系。

### 🔹 Android 17 适配测试矩阵
覆盖 targetSdk 36/37、经典蓝牙 RFCOMM、LE CoC、远端主动断开、本地关闭 socket、飞行模式、蓝牙开关、后台限制和弱信号场景。

## 扩展

### 🔸 与 11.6 Bluetooth 功耗章节的边界
11.6 负责扫描、连接和后台功耗；本节聚焦 socket 读写语义、断线状态机和长连接治理。

### 🔸 与 24.14 弱网治理的关系
Bluetooth 不是蜂窝或 Wi-Fi 弱网，但重连退避、请求分段和状态上报可以复用 24.14 的治理框架。

### 🔸 与 26.17 线上网络质量监控的关系
线上监控需要把 Bluetooth socket 断开归入独立通道，不混入 HTTP 错误率或公网弱网指标。

<!-- outline-end -->

> 本节内容待加工。
