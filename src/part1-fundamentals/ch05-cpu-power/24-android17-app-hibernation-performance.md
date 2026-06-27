---
title: "Android 17 App Hibernation 状态机与冷启动恢复性能"
chapter: "5.24"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [app-hibernation, app-standby, background-limits, power-management, cold-restart]
related_chapters: ["5.8", "5.21", "5.17", "1.20"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构/官方文档"
---

# 5.24 Android 17 App Hibernation 状态机与冷启动恢复性能

<!-- outline-start -->
## 要点

### 🔹 App Hibernation 与 App Standby / App Archiving 的区分
- App Standby Bucket：限制后台执行频率（运行频率降级）
- App Hibernation：长时间未使用（数月）后系统自动撤销运行时权限、清除缓存、强制停止
- App Archiving：用户或系统触发的 APK 半卸载（保留数据），需要重新下载安装
- 三者的触发条件、系统行为、恢复路径不同，性能影响也不同

### 🔹 AppHibernationService 系统架构
- 服务位置：frameworks/base/services/core/java/com/android/server/apphibernation/AppHibernationService.java
- 状态存储：system/home/<user>/app_hibernation/ 目录下以包名组织的状态文件
- 检查周期：JobScheduler 驱动的周期性检查（通常每 24h 一次）
- 检查输入：UsageStatsManager 提供的 lastTimeVisible 指标

### 🔹 Hibernation 状态转换条件
- 进入条件：App 连续 N 天（默认 90 天 Android 12，逐步调整至更短）未被前台使用
- Android 13+ 扩展：未使用阈值可由 OEM 通过 DeviceConfig 调整
- Android 15+ 强化：短信息和通知交互不再算作"使用"
- Android 17 行为：进一步收紧交互判定标准，后台 Service 运行不算"活跃使用"

### 🔹 Hibernation 对应用状态的具体影响
- 运行时权限全部撤销（ACCESS_FINE_LOCATION、RECORD_AUDIO 等）
- Cache 目录被清除（getCacheDir()、getExternalCacheDir()）
- 应用被 force-stop，不再接收隐式广播
- JobScheduler 和 AlarmManager 任务被取消
- 文件级存储不被清除（getFilesDir()、数据库不受影响）

### 🔹 从 Hibernation 恢复的冷启动性能
- 权限恢复延迟：首次启动需要重新申请权限，增加了用户交互路径
- Cache 重建开销：缓存数据丢失导致首次启动需要重新下载/计算
- 进程冷启动：进程已被 force-stop，等同于全冷启动（无温启动优势）
- 与正常冷启动的性能差异测量：P95 延迟差异来源分析
- Google Play 的 "Restricted" 标记与 Hibernation 状态联动

### 🔹 Hibernation 状态观测与调试
- `adb shell am get-hibernation-states`（Android 12+）
- `adb shell cmd app_hibernation <command>` 调试接口
- dumpsys app_hibernation 输出字段解读
- UsageStatsManager.queryEventsForSelf() 判断应用是否即将进入 hibernation
- Perfetto 中 hibernation 相关的系统事件 atrace 轨道

### 🔹 应用侧 Hibernation 适配策略
- 检测应用是否从 hibernation 恢复：权限检查 + cache 状态 + 启动标记
- 关键数据的持久化策略：不依赖 cache，重要数据写入 filesDir 或数据库
- 用户引导重新授权的最佳实践
- 前台服务保活与 hibernation 的关系（短时 FGS 不阻止 hibernation）
- ExemptionMechanism：DPC 管控设备上的豁免机制

## 扩展

### 🔸 Hibernation 与 Doze / App Standby 的叠加效应
- Doze 管设备级休眠，App Standby 管单 app 级别频率限制，Hibernation 管长期未使用的极端限制
- 三者同时生效时的优先级和叠加行为
- OEM 定制层（如 MIUI、ColorOS）的扩展休眠策略差异

### 🔸 Android 17 Hibernation 与 Privacy Sandbox 的交互
- Privacy Sandbox Topics/Protected Audience 在 hibernation 状态下的行为
- FLEDGE custom audience 在 app 被 hibernated 后的生命周期

### 🔸 Hibernation 对 APM / 崩溃监控的影响
- Hibernated app 的 crash 上报链路是否正常工作
- Hibernation 触发的 force-stop 在 ApplicationExitInfo 中的归因标记

<!-- outline-end -->

> 本节内容待加工。
