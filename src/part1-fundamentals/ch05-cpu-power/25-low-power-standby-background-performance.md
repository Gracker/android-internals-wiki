---
title: "Android Low Power Standby 深度休眠与后台任务性能边界"
chapter: "5.25"
status: draft
applicable_versions: "Android 15 (API 35) - Android 17 (API 37)"
tags: [low-power-standby, power-management, background-tasks, deep-sleep, sensor-batching]
related_chapters: ["5.6", "5.8", "5.17", "11.3", "5.21"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "AOSP结构/官方文档"
---

# 5.25 Android Low Power Standby 深度休眠与后台任务性能边界

<!-- outline-start -->
## 要点

### 🔹 Low Power Standby 定位与设计目标
- Android 15 引入的系统级深度省电模式，设备长时间静止且屏幕关闭时自动进入
- 与 Doze 的关系：Doze 是短周期休眠（数分钟到数小时），Low Power Standby 是长时间稳定休眠
- 典型触发场景：夜间放置在桌面、长时间不操作的车载支架等
- 目标：将设备 CPU 唤醒频率压到最低，传感器采样降至最小窗口

### 🔹 触发条件与状态机
- 进入条件：屏幕关闭 + 设备静止（加速度计判定）+ 持续时间超过阈值
- PowerManagerService 中的状态管理：LowPowerStandbyController 实现
- AOSP 源码位置：frameworks/base/services/core/java/com/android/server/power/
- 与 Ambient Display、Always-on Display 的交互边界
- Android 16/17 对触发条件的调整：增加光照传感器辅助判定

### 🔹 Low Power Standby 对后台任务的限制清单
- JobScheduler：非紧急任务被延迟到退出 Low Power Standby 后执行
- AlarmManager：精确闹钟（setExact）不受影响，非精确闹钟被延迟
- FGS：前台服务可以继续运行但受到额外 CPU 限制
- 网络访问：后台网络可能被暂时挂起
- SensorManager：传感器批处理间隔被强制拉长
- LocationManager：后台位置更新频率大幅降低

### 🔹 对应用性能的实际影响测量
- 典型场景测试：即时通讯 App 消息延迟、邮件同步延迟、闹钟 App 准时性
- Low Power Standby 进入/退出对 CPU 频率调度的影响
- 传感器批处理间隔变化：从 ms 级到秒级的退化测量
- 网络连接保活：TCP keepalive 在 Low Power Standby 下的行为

### 🔹 应用适配与最佳实践
- 检测 Low Power Standby 状态：PowerManager.isLowPowerStandbyEnabled()（API 35+）
- 关键任务的保障策略：使用 setExact 闹钟、FGS、或 WorkManager expedited job
- 消息推送策略调整：FCM 高优先级消息在 Low Power Standby 下的投递保证
- 传感器数据补偿：退出 Low Power Standby 后的批处理数据补全策略
- 用户引导：告知用户将应用加入豁免列表的方法和代价

### 🔹 调试与验证方法
- adb 模拟 Low Power Standby 状态切换
- dumpsys power 中 LowPowerStandby 相关字段解读
- Perfetto trace 中 LowPowerStandby 进入/退出事件的识别
- Battery Historian 中 Low Power Standby 时段的功耗分析
- 自动化测试脚本编写：模拟设备静止 + 屏幕关闭场景

## 扩展

### 🔸 OEM 实现差异
- Pixel 设备的 Low Power Standby 实现细节
- Samsung/Xiaomi 等厂商对 Low Power Standby 的定制化扩展
- CDD 要求 vs 实际实现差异

### 🔸 Low Power Standby 与端侧 AI 推理
- 端侧模型在 Low Power Standby 下的推理调度延迟
- ADPF Hint Session 在 Low Power Standby 下的行为
- 后台语音监听（hotword detection）在 Low Power Standby 下的保障机制

<!-- outline-end -->

> 本节内容待加工。
