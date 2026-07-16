---
title: "OEM 厂商差异化后台限制与功耗诊断实战"
chapter: "25.25"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [oem-doze, background-restriction, power-optimization, vendor-doze, chinese-oem]
related_chapters: ["25.2", "25.3", "25.4", "25.13", "11.2", "11.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "research-gaps+daily-info"
confidence: medium
---

# 25.25 OEM 厂商差异化后台限制与功耗诊断实战

<!-- outline-start -->
## 要点

### 🔹 中国厂商后台管控策略全景
- 小米 MIUI 的「神隐模式」与后台清理机制
- 华为 EMUI/HarmonyOS 的省电策略与「应用启动管理」
- OPPO ColorOS 的后台冻结与智能省电
- vivo OriginOS 的后台管理策略
- 三星 One UI 的睡眠模式与自适应电池
- 各厂商策略与 AOSP 原生 Doze/App Standby 的差异对比

### 🔹 厂商差异化对应用后台行为的影响
- 后台 Service 存活率差异（同一应用在不同厂商设备上的表现）
- AlarmManager 精确闹钟的投递可靠性差异
- JobScheduler / WorkManager 任务执行的延迟与被杀
- FCM/推送通道到达率与厂商心跳策略的关系
- 前台服务通知在不同厂商 ROM 上的显示与保活差异

### 🔹 系统级诊断工具与 API
- `dumpsys deviceidle` 查看原生 Doze 状态
- `dumpsys jobscheduler` 查看任务调度队列与配额
- `cmd appops` 查询应用操作权限（RUN_IN_BACKGROUND 等）
- `dumpsys activity processes` 分析进程优先级与 oom_adj
- 厂商私有诊断接口（如小米的 `dumpsys miui-background`）
- adb 命令模拟后台限制场景进行测试

### 🔹 AppStandby Bucket 在厂商 ROM 上的变异
- AOSP 标准 Bucket（ACTIVE/WORKING_SET/FREQUENT/RARE/RESTRICTED）
- 厂商自定义 Bucket 或等效限制机制
- Bucket 降级触发的额外条件（厂商自有的使用频率判定）
- 应用被降级后的实际行为差异（Job 配额、网络访问、Alarm 投递）

### 🔹 国内外应用的后台保活策略选择
- 白名单申请（REQUEST_IGNORE_BATTERY_OPTIMIZATIONS）的正确使用与厂商适配
- 前台服务保活的适用场景与厂商限制
- WorkManager + Expedited Job 的可靠性边界
- 推送通道集成（FCM + 厂商推送如华为 HMS Push、小米 Push）的策略
- 用户引导式保活（引导用户关闭厂商限制）的最佳实践

### 🔹 功耗归因：区分 AOSP 行为与厂商行为
- BatteryStats 中厂商自定义功耗归因项识别
- BatteryStatsService 历史记录中的厂商标记
- 如何通过 Perfetto/systrace 识别厂商注入的后台限制事件
- 厂商 ROM 中 Power HAL 自定义 hint 对功耗统计的影响

## 扩展

### 🔸 厂商后台限制的自动化测试方案
- 使用 UIAutomator + adb 模拟厂商后台限制
- 构建「厂商兼容性矩阵」测试框架

### 🔸 反向工程厂商后台限制
- 通过 logcat 标签识别厂商后台管控组件
- 使用 Frida/Xposed hook 厂商系统服务进行行为分析

### 🔸 Android 17 对厂商后台限制的规范化趋势
- Android 17 引入的 `BackgroundAccessDialog` 与用户可见的后台权限
- Google Play 政策对厂商后台限制的影响

<!-- outline-end -->

> 本节内容待加工。

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
[缺口来源: intake/research-gaps.md — "厂商差异化省电策略的系统排查指南" — 重要程度：高]

<!-- AIW-源码调研-2026-07-16 -->
## 🔹 AOSP 架构重构：AppStateManager → AppRestrictionController + Tracker 模式

android-17.0.0_r1 中已无 `AppStateManager.java`，实际采用组合架构：

**核心控制器**：`AppRestrictionController.java`  
**追踪器体系**：7 个 `BaseAppStateTracker` 子类（AppBatteryTracker, AppBatteryExemptionTracker, AppFGSTracker, AppMediaSessionTracker, AppPermissionTracker, AppBroadcastEventsTracker, AppBindServiceEventsTracker）

```java
// AppRestrictionController 初始化追踪器链
mAppStateTrackers.add(mAppBatteryTracker);
mAppStateTrackers.add(mAppBatteryExemptionTracker);
mAppStateTrackers.add(mAppFGSTracker);
mAppStateTrackers.add(mAppMediaSessionTracker);
mAppStateTrackers.add(mAppPermissionTracker);
```

### 🔹 OEM 接口边界：SystemConfig 豁免机制

厂商通过 `SystemConfig` 配置豁免应用：

```java
// SystemConfig.java 中解析豁免配置
case "bg-restriction-exemption":
    readBgRestrictionExemption(parser, permFile, allowOverrideAppRestrictions, name);
    break;

// AppRestrictionController.java 获取豁免列表
private void initBgRestrictionExemptioFromSysConfig() {
    final SystemConfig sysConfig = SystemConfig.getInstance();
    mBgRestrictionExemptioFromSysConfig = sysConfig.getBgRestrictionExemption();
    for (int i = exemptedPkgs.size() - 1; i >= 0; i--) {
        Slog.i(TAG, "bg-restriction-exemption: " + exemptedPkgs.valueAt(i));
    }
}
```

### 🔹 多层级豁免规则链

豁免优先级（从高到低）：
1. **系统模块**：`isSystemModule(pkg)` → `REASON_SYSTEM_MODULE`
2. **运营商应用**：`isCarrierApp(pkg)` → `REASON_CARRIER_PRIVILEGED_APP`
3. **系统豁免列表**：`isExemptedFromSysConfig(pkg)` → `REASON_SYSTEM_ALLOW_LISTED`
4. **设备管理员**：`isActiveDeviceAdmin(pkg, userId)` → `REASON_ACTIVE_DEVICE_ADMIN`
5. **角色持有**：`isRoleHeldByUid(ROLE_DIALER/EMERGENCY, uid)` → `REASON_ROLE_DIALER/EMERGENCY`
6. **豁免列表**：`isOnDeviceIdleAllowlist(uid)` → `REASON_ALLOWLISTED_PACKAGE`
7. **关联设备管理器**：`isAssociatedCompanionApp(userId, uid)` → `REASON_COMPANION_DEVICE_MANAGER`

### 🔹 厂商差异化诊断：豁免时间窗口控制

**AppBatteryExemptionTracker 实现关键逻辑**：

```java
@Override
public void onStateChange(int uid, String packageName, boolean start, long now, int stateType) {
    final SparseArray<ArrayMap<String, Integer>> map = mUidPackageStates.getMap();
    ArrayMap<String, Integer> pkgsStates = map.get(uid);
    
    // 关键：同 UID 下只允许一个豁免实例
    if (start) {
        boolean alreadyStarted = false;
        for (int i = pkgsStates.size() - 1; i >= 0; i--) {
            final int s = pkgsStates.valueAt(i);
            if ((s & stateType) != 0) {
                alreadyStarted = true;  // 已有同类型豁免
                break;
            }
        }
        if (!alreadyStarted) {
            // 启动豁免窗口
            addEvent = true;
        }
    }
}
```

### 🔹 厂商限制的进程级影响

**RESTRICTION_LEVEL 等级定义**：
- `RESTRICTION_LEVEL_EXEMPTED = 20`：完全豁免
- `RESTRICTION_LEVEL_ADAPTIVE_BUCKET = 30`：正常
- `RESTRICTION_LEVEL_RESTRICTED_BUCKET = 40`：限制
- `RESTRICTION_LEVEL_BACKGROUND_RESTRICTED = 50`：后台限制
- `RESTRICTION_LEVEL_FORCE_STOPPED = 60`：强制停止

**AMS 后台限制应用**：
```java
public void noteAppRestrictionEnabled(String packageName, int uid,
        @RestrictionLevel int restrictionType, boolean enabled,
        @RestrictionReason int reason, String subReason) {
    
    mAppRestrictionController.noteAppRestrictionEnabled(packageName, uid, 
            restrictionType, enabled, reason, subReason, source, threshold);
}
```

### 🔹 厂商诊断工具链

**一键诊断脚本**：
```bash
# 检查豁免状态
adb shell cmd activity background get-restriction-level <package>
adb shell dumpsys activity bg-restriction exemption

# 检查限制等级  
adb shell dumpsys activity restriction <package>

# 检查豁免原因
adb shell dumpsys activity bg-restriction exemption-reason <uid>

# 检查豁免追踪器
adb shell dumpsys activity restriction trackers
```

**豁免持久化路径**：`/data/system/apprestriction/settings.xml`

<!-- AIW-源码调研-2026-07-16 -->
