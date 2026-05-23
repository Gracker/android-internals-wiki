---
title: "Android 17 后台音频硬化与播放功耗治理"
chapter: "25.17"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [power, audio, foreground-service, android-17, media-playback]
related_chapters: ["1.16", "5.8", "8.8", "11.2", "16.5", "25.13", "26.17"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-24"
gap_source: "官方文档/已有章节深挖/每日信息"
sources:
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/bg-audio"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/17/release-notes"
  - type: clippings-structure
    path: "Clippings/Android 性能优化 - Android 性能优化总结.md"
---

# 25.17 Android 17 后台音频硬化与播放功耗治理

<!-- outline-start -->
## 要点

### 🔹 后台音频硬化的触发条件
梳理 Android 17 对后台播放、音频焦点请求和音量控制的限制范围，区分所有应用生效与 `targetSdkVersion >= 37` 生效的行为差异。

### 🔹 FGS、while-in-use 与闹钟用途豁免
说明 `mediaPlayback` 前台服务、while-in-use 能力、exact alarm 权限和 `USAGE_ALARM` 之间的组合关系，避免把 FGS 类型声明误当成通行证。

### 🔹 播放链路上的失败信号
整理 `AudioManager.requestAudioFocus()`、MediaSession 状态、播放器回调、`AudioTrack` 写入停止和系统日志之间的对应关系，用于定位“后台无声”“焦点申请失败”“音量控制无效”。

### 🔹 长时播放的功耗预算
从音频 offload、buffer 配置、网络保活、WakeLock、蓝牙输出和解码线程几个角度建立功耗检查清单，避免用保活手段掩盖播放状态管理问题。

### 🔹 Perfetto、dumpsys 与 logcat 取证
给出 `audio` trace、`dumpsys audio`、`dumpsys media_session`、FGS 状态、网络和电量统计的组合观察点，把播放中断和功耗异常放到同一条时间线上分析。

### 🔹 Android 17 适配与灰度验证
设计 `targetSdkVersion 37` 前后的回归场景：锁屏、退后台、定时提醒、蓝牙播放、弱网恢复、耳机拔插和通知控制，输出可复查的测试矩阵。

## 扩展

### 🔸 与 Foreground Service 超时和 JobScheduler 配额的关系
后台音频不能只看音频 API，还要对照 §25.13 中的 FGS 超时、启动限制和后台任务配额。

### 🔸 蓝牙、LE Audio 与车机场景
长时播放经常落在蓝牙、车机和可穿戴设备场景，需要单独观察连接状态、音频路由和设备侧功耗。

### 🔸 OEM 后台策略差异
厂商系统可能对后台播放、通知常驻和电池优化有额外策略，后续可补充不同设备的实测矩阵。

### 🔸 线上指标设计
候选指标包括后台播放中断率、音频焦点失败率、播放 session 异常结束、后台耗电分位值和用户手动重启播放比例。

<!-- outline-end -->

> 本节内容待加工。
