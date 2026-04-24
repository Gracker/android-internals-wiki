---
title: "耗电与发热监控 (Battery & Thermal)"
chapter: "19"
section: "19.25"
status: ready-for-review
drafted_date: "2026-04-24"
drafted_by: "gemini"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-04-24"
confidence: high
tags: [apm, battery, thermal, wakelock]
related_chapters: ["19.0", "19.19"]
pipeline_stage: task6_pending
---

# 耗电与发热监控 (Battery & Thermal)

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明电量与发热是影响用户卸载 App 的核心隐性因素，解析线上 APM 如何突破系统限制进行归因监控。
- 🔹 [Wakelock 泄漏监控] 解释 `PowerManager.WakeLock` 的申请与释放原理，介绍如何通过 ASM 字节码插桩或动态代理拦截，找出忘记释放唤醒锁的代码堆栈。
- 🔹 [Alarm 唤醒风暴] 说明后台频繁 Alarm 唤醒对系统 Doze 模式的破坏，以及如何在端侧记录异常的高频定时任务。
- 🔹 [硬件资源耗电归因] 拆解网络模块（基带唤醒）、GPS 定位、蓝牙扫描以及后台异常高 CPU 占用在端侧的统计方法。
- 🔹 [Thermal API 应用] 重点介绍 Android 10+ 引入的 `PowerManager.OnThermalStatusChangedListener`，如何感知设备的过热状态（如 `THERMAL_STATUS_SEVERE`）。
- 🔹 [端侧降级策略] 结合发热状态感知，给出 App 主动自保的降级策略：降低动画帧率、关闭后台预加载、停止大文件下载、降低视频分辨率。
- 🔹 [系统级耗电账单] 分析 Android Vitals 提供的“后台耗电”及“卡死导致的耗电”大盘数据与端侧监控的互补关系。

### 扩展（可选深入）

- 🔸 提供一段基于 Android 10 Thermal API 进行业务降级的架构伪代码。
- 🔸 画一张从“触发 CPU/网络高频活动”到“发热状态改变”再到“APM 端侧报警”的反馈链路图。
- 🔸 介绍 `BatteryManager` 获取电流/电压瞬时值的局限性及不同厂商 ROM 下的差异。

### 流水线加工要求

- 必须明确“耗电”是一个衍生指标，直接测电量下降往往是不准的，关键是测“谁占用了高耗电硬件”。
- 必须指出后台任务 (WorkManager/JobScheduler) 也是耗电分析的重灾区。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
<!-- outline-end -->
