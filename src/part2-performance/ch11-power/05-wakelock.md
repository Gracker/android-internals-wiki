---
title: "Wakelock 机制与功耗分析"
chapter: "11.5"
status: draft
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [wakelock, power, battery, alarmmanager, doze, batterystats, kernel-wakelock]
related_chapters: ["5.6", "5.8", "11.1", "11.2", "11.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-06"
gap_source: "研究素材+AOSP结构+官方文档+读者需求"
---

# 11.5 Wakelock 机制与功耗分析

<!-- outline-start -->
## 要点

### 🔹 锚点 1：Wakelock 的本质——为什么 Android 需要"阻止睡眠"
- Wakelock 的底层实现：内核 wake_lock 机制与 PowerManagerService 的映射关系
- 四种 Wakelock 类型（PARTIAL_WAKE_LOCK、FULL_WAKE_LOCK、SCREEN_DIM_WAKE_LOCK、SCREEN_BRIGHT_WAKE_LOCK）的设计意图与演进（后三种已废弃）
- Partial Wakelock 与 CPU 睡眠的关系：持有期间 CPU 不会进入低功耗状态
- 为什么 Wakelock 是 Android 功耗问题的头号杀手（Google Play 的 wakelock 惩罚政策）

### 🔹 锚点 2：Wakelock 的获取、持有与释放全流程
- PowerManager.acquire() → PowerManagerService.acquireWakeLock() 的完整调用链
- WakeLock 内部数据结构：WakeLockToken、IBinderDeathRecipient、WorkSource
- 引用计数模式（ref-counted）与非引用计数模式的差异与常见坑
- setReferenceCounted() 的行为：为什么必须配对 acquire/release
- WorkSource 的作用：标记 wakelock 归属，用于电池统计归因

### 🔹 锚点 3：Android 电源状态机与 Wakelock 的位置
- Android 电源状态图：Awake → Screen Dim → Screen Off → Sleep → Wakeup
- Wakelock 在状态转换中的作用：Partial Wakelock 阻止 Screen Off → Sleep 转换
- Doze 模式对 Wakelock 的压制：maintenance window 之外 wakelock 被系统忽略
- App Standby Bucket 对 wakelock 行为的影响（Active → Restricted 的配额递减）
- Android 12+ 前台服务通知与 wakelock 的联动

### 🔹 锚点 4：内核 Wakelock 与用户态 Wakelock 的区别
- Linux 内核 wake_lock / wake_source 机制（/sys/power/wake_lock）
- Android PowerManagerService 的用户态 wakelock 与内核 wakelock 的映射
- kernel wakelock 的来源：Binder 驱动、Alarm 驱动、Input 设备、modem 等
- 如何通过 /proc/wakelocks 或 /sys/kernel/debug/wakeup_sources 查看内核级 wakelock
- 用户态 wakelock 泄漏如何间接导致内核 wakelock 无法释放

### 🔹 锚点 5：Wakelock 泄漏的常见模式与诊断
- 常见泄漏模式：acquire 后异常路径未 release、异步回调未到达、生命周期不匹配
- Battery Historian 中的 wakelock 可视化：top bar 中的 wakelock 时间线
- dumpsys batterystats 中 wakelock 统计的解读：全量时间 vs 持有次数 vs 后台时间
- Perfetto 中 PowerManagerService track 的 wakelock 事件
- Android 17 新增：AlarmManager.OnAlarmListener 回调变体减少 wakelock 持有时长

### 🔹 锚点 6：AlarmManager 与 Wakelock 的关系
- AlarmManager 触发机制：setExact() / setExactAndAllowWhileIdle() / setAndAllowWhileIdle()
- 每次 Alarm 触发都会持有 wakelock：BroadcastReceiver.onReceive() 期间的 wakelock 生命周期
- Android 17 的 OnAlarmListener 回调变体：进程内直接回调，避免启动 Receiver 的开销
- Google Play 的 wakelock 惩罚政策（2h/24h 阈值 + 5% session + 28 天窗口）
- 最佳实践：使用 WorkManager / JobScheduler 替代手动 AlarmManager + Wakelock 组合

### 🔹 锚点 7：Wakelock 的替代方案与最佳实践
- WorkManager 的 wakelock 管理：Jetpack 内部管理 wakelock 生命周期
- Foreground Service 的 wakelock 特权与限制
- Coroutine + lifecycle-aware 的 wakelock 封装模式
- Android 16+ 后台执行配额对 wakelock 使用的约束
- Google 官方推荐：从显式 wakelock 迁移到系统管理的后台调度

## 扩展

### 🔸 扩展点 1：AOD Min Mode 与 Wakelock
- Android 17 AOD Min Mode 的全屏低功耗 monochrome UI 模式
- Min Mode 如何在极低功耗状态下提供交互能力
- 与传统 wakelock 的关系：Min Mode 替代了部分 partial wakelock 的使用场景

### 🔸 扩展点 2：Battery Stats 深度分析
- dumpsys batterystats --checkin 格式解析
- Wakelock 统计中的 "Kernel only" vs "User" 区分
- 历史电池数据的时间线回溯分析
- UIDT (Usage Idle Time) API 作为 wakelock 的替代信号

<!-- outline-end -->

> 本节内容待加工。
