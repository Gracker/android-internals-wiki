---
date: 2026-04-06
time: "07:01"
source: task5-research-discovery
focus: "功耗优化（topic rotation #6）+ Android 17 功耗/渲染管线变更"
rotation_topic: 6
candidates: 6
passed: 2
delivered: 2
status: delivered
---

# Android 17 功耗管理新特性 + Play Store Wake Lock 政策

## Theme 1: AlarmManager OnAlarmListener + Play Store Wake Lock 惩罚政策

### 摘要
Android 17 引入 `AlarmManager.setExactAndAllowWhileIdle` 的 `OnAlarmListener` 回调变体，替代传统 `PendingIntent`，显著降低 wakelock 时长。同步推出 Play Store 过度 wakelock 惩罚政策（2026年3月1日生效），以 Samsung 联合制定标准。

### 关键事实

**1. AlarmManager.setExactAndAllowWhileIdle(OnAlarmListener) — Android 17 新 API**

- **机制变更**：从 PendingIntent（跨进程 IPC → Intent 解析 → BroadcastReceiver/Service 启动）改为 OnAlarmListener（进程内直接回调分发）
- **功耗收益**：
  - 避免 PendingIntent 的跨进程通信开销和 Intent 解析
  - 减少 component 生命周期启动开销（不再需要 instantiate BroadcastReceiver/Service）
  - 缩短 partial wakelock 持有时长
- **限制**：
  - 不持久化：app 进程被杀或设备重启后 alarm 丢失
  - 单实例规则：每个 OnAlarmListener 实例只能关联一个 scheduled alarm
  - 适用场景：配合 long-lived Foreground Service 使用（确保进程存活）
- **适用场景**：即时通讯 socket 心跳、医疗监测定时上报、需要在 Doze/Battery Saver 下精确触发的周期任务

**2. Play Store Wake Lock 惩罚政策（2026-03-01 生效）**

- **阈值定义**：非豁免 partial wake lock 累计 >2小时/24小时 AND 影响 >5% 用户 session（28天窗口）
- **惩罚措施**：
  - Play Store 搜索/推荐降权
  - App 详情页显示「可能加速耗电」警告标签
- **豁免类型**：音频播放、位置访问、用户主动发起的数据传输（UIDT API）
- **联合制定**：Google + Samsung
- **开发者工具**：Play Console Android Vitals dashboard 可追踪 wakelock 指标
- **替代方案**：WorkManager、User-Initiated Data Transfer (UIDT) API

### 可引用段落

> Android 17 新增 `AlarmManager.setExactAndAllowWhileIdle` 的 OnAlarmListener 回调变体。与传统 PendingIntent 方式不同，OnAlarmListener 在 app 进程内直接分发回调，避免了跨进程 IPC、Intent 解析以及 BroadcastReceiver/Service 组件实例化的开销，从而显著缩短 partial wakelock 持有时长。开发者需注意：OnAlarmListener 方式的 alarm 不持久化（进程被杀或设备重启后丢失），且每个实例同一时刻只能关联一个 alarm。最佳实践是将此 API 与 long-lived Foreground Service 配合使用。

> 2026年3月1日起，Google Play Store 实施过度 wakelock 惩罚政策（与 Samsung 联合制定）。当 app 的非豁免 partial wake lock 在24小时内累计超过2小时，且此行为影响超过5%用户 session（28天窗口），该 app 将面临 Play Store 推荐降权和详情页耗电警告标签。豁免场景包括音频播放、位置服务和用户主动数据传输。开发者应通过 Play Console Android Vitals 监控 wakelock 指标，优先迁移至 WorkManager 或 UIDT API。

### 目标章节
- **§5.6 Android 功耗管理**：Doze/AlarmManager 新 API + wakelock 最佳实践更新
- **§5.8 后台执行限制与优化**：wake lock 政策影响 + WorkManager/UIDT 替代方案
- **§11.2 App 耗电优化**：Play Store 政策作为优化驱动力 + Vitals 监控
- **§15.5 线上性能监控**：Android Vitals wakelock 监控指标

### 验证状态
- [已验证] AlarmManager OnAlarmListener API — android.com 官方文档
- [已验证] Play Store wakelock 阈值（2h/24h, 5% sessions, 28d window）— googleblog.com + android.com
- [已验证] Samsung 联合制定 — samsung.com
- [待验证] OnAlarmListener 功耗收益量化数据（wakelock 时长缩短百分比）

---

## Theme 2: Android 17 AOD "Min Mode" + 极端省电模式增强

### 摘要
Android 17 引入 AOD（Always-On Display）"Min Mode"，允许 app 在低功耗显示状态下提供全屏交互界面（如 Google Maps 单色导航）。同步增强 Extreme Battery Saver，Samsung One UI 9 引入 "Maximum mode"。

### 关键事实

**1. AOD Min Mode — 全屏低功耗交互界面**

- **定位**：从传统 AOD（时间/通知/简单图标）进化为全屏低功耗 app 界面
- **技术特征**：
  - 复用 AOD 低功耗显示技术（limited screen brightness + reduced refresh rate）
  - 全屏 monochrome 界面
  - 无需完全唤醒设备即可提供 rich glanceable 信息
- **首批适配**：Google Maps（低功耗单色导航界面）
- **开发者接入**：通过特定 API 注册 Min Mode 界面（细节待官方文档发布）
- **功耗基线**：传统 AOD 日均消耗 10-15% 电量，Min Mode 目标是在提供更多功能的同时保持可比功耗

**2. Extreme Battery Saver / Maximum mode 增强**

- **Android 17 系统级**：
  - 更激进的后台活动限制
  - 暂停大部分非必要 app + 停止通知
  - 用户可自定义白名单 app
- **Samsung One UI 9 "Maximum mode"**：
  - 极端省电模式的增强版本
  - 与 Android 17 协同（Samsung 作为 Wake Lock 政策联合制定方）
- **AutoFDO kernel optimization**：
  - 利用真实使用数据的反馈导向优化
  - 冷启动加速 + 后台任务更流畅
  - 降低不必要的 CPU 处理

### 可引用段落

> Android 17 引入 AOD "Min Mode"，允许应用在 Always-On Display 的低功耗显示状态下提供全屏交互界面。Min Mode 复用 AOD 的低功耗显示管线（限制亮度和刷新率），但支持全屏 monochrome UI，使应用无需唤醒设备即可传递丰富信息。Google Maps 将作为首批适配者，提供低功耗单色导航界面。传统 AOD 日均消耗约 10-15% 电量，Min Mode 的设计目标是在提供更多功能的同时维持可比的功耗水平。

> Android 17 的 Extreme Battery Saver 模式进一步收紧后台活动限制，暂停大部分非必要应用并停止其通知推送。Samsung 在基于 Android 17 的 One UI 9 中引入 "Maximum mode" 极端省电方案。值得注意的是，Samsung 与 Google 联合制定了 Play Store 的 wakelock 惩罚政策，表明功耗优化已从系统层面扩展到应用生态治理层面。

### 目标章节
- **§5.6 Android 功耗管理**：AOD Min Mode + Extreme Battery Saver 演进
- **§11.2 App 耗电优化**：app 层面适配 Min Mode 的最佳实践
- **§11.3 系统级功耗优化**：AutoFDO kernel + 极端省电模式
- **§2.9 渲染机制的版本演进**：AOD 渲染管线的低功耗模式变更

### 验证状态
- [已验证] AOD Min Mode 功能描述 — android.com + androidauthority.com
- [已验证] Google Maps Min Mode 导航 — androidheadlines.com + gadgethacks.com
- [已验证] Samsung One UI 9 Maximum mode — samsung.com
- [待验证] Min Mode API 接入方式（开发者文档尚未完全公开）
- [待验证] Min Mode 具体功耗数据（10-15% AOD 基线来源：gadgethacks.com）
