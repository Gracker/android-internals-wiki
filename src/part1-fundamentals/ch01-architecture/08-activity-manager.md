---
title: "Activity Manager Service 与性能分析"
chapter: "1.8"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [ams, activity-manager, process-lifecycle, anr, service-management, broadcast, content-provider]
related_chapters: ["1.3", "1.4", "9.1", "9.2", "8.2", "5.8"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-04"
gap_source: "AOSP结构+官方文档+研究素材+读者需求"
---

# 1.8 Activity Manager Service 与性能分析

<!-- outline-start -->
## 要点

### 🔹 AMS 在 Android 架构中的角色
- AMS 是 Android 最核心的系统服务之一，运行在 system_server 进程中
- 管理四大组件（Activity/Service/BroadcastReceiver/ContentProvider）的生命周期
- 与其他核心服务的交互关系（PMS/WMS/SurfaceFlinger/ProcessList）
- 在 Perfetto 中如何定位 AMS 相关的 Track 和事件

### 🔹 AMS 的进程管理机制
- 进程优先级（oom_adj）的动态调整策略
- 进程启动流程：startActivity → AMS → Zygote fork → Application.onCreate
- 进程回收策略：lmkd 与 AMS 的协作（详见 §4.4 LMK）
- Cached/Empty 进程的管理与回收时机
- 在 Perfetto 中观察进程状态变化（proc track / oom_adj 变化事件）

### 🔹 AMS 与 ANR 检测
- ANR 的监控入口：AMS 中的各种超时机制
- Input ANR、Broadcast ANR、Service ANR、ContentProvider ANR 的触发路径
- AMS 的 ANR 数据采集流程（dump stack traces、CPU 使用率）
- AnrHelper 与 ProcessErrorStateRecord 的异步处理管线
- 在 Perfetto 中 AMS 如何记录 ANR 事件（anr trace / am_anr event）

### 🔹 AMS 的 Activity 管理
- Activity 栈（TaskStack）与 Task 管理
- Activity 启动流程的完整链路：从 startActivity() 到窗口显示
- Activity 生命周期回调的时序（onCreate→onStart→onResume→onPause→onStop→onDestroy）
- Android 17 recreateOnConfigChanges 对 Activity 重启的影响
- Activity 启动耗时在 Perfetto 中的定位（am_proc_start / am_activity_launch）

### 🔹 AMS 的 Service 管理
- Service 的绑定与启动机制
- 前台服务（Foreground Service）的演进与限制（Android 12→17）
- FGS 类型声明要求（Android 14+ 的 foregroundServiceType）
- Service ANR 超时机制的版本演进
- 后台启动服务的限制链（Android 8.0→17 的逐步收紧）

### 🔹 AMS 的广播管理
- 广播的分发机制（有序广播/无序广播/本地广播）
- BroadcastQueue 的实现与调度策略
- 广播超时（前台 10s / 后台 60s）的监控机制
- 静态广播与动态广播的性能差异
- Android 14+ 的 BACKPORTED_BROADCAST_EXTRAS 限制

### 🔹 AMS 在 Perfetto 中的具体表现
- system_server 进程中的 AMS 相关线程（ActivityManager、Binder:system）
- 关键 Trace 事件：am_proc_start、am_proc_died、am_anr、am_crash、am_activity_launch
- AMS 与其他服务的 Binder 调用在 Trace 中的可见性
- 典型场景的 Trace 特征：冷启动、ANR、进程被杀、配置变更

## 扩展

### 🔸 AMS 内部的锁竞争与性能瓶颈
- AMS 使用全局锁（mService/ mHandler）的竞态场景
- system_server 的 Binder 线程池饱和问题
- 大量并发组件请求时 AMS 的调度策略

### 🔸 AMS 的厂商定制与优化
- 各厂商（MTK/高通/三星）对 AMS 的定制点
- 厂商如何调整 oom_adj 策略和进程回收时机
- 厂商如何优化 AMS 的启动速度和响应延迟

### 🔸 AMS 的版本演进与行为变更
- Android 12: 精确闹钟限制 + 后台启动限制 + FGS 通知延迟
- Android 14: FGS 类型声明 + 全屏 Intent 限制
- Android 16: ProfilingManager 系统触发式追踪
- Android 17: recreateOnConfigChanges + 后台执行限制进一步收紧

<!-- outline-end -->

> 本节内容待加工。
