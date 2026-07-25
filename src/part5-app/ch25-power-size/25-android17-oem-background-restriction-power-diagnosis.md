---
title: "OEM 厂商差异化后台限制与功耗诊断实战"
chapter: "25.25"
status: finalized
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [oem-doze, background-restriction, power-optimization, vendor-doze, chinese-oem]
related_chapters: ["25.2", "25.3", "25.4", "25.13", "11.2", "11.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-16"
gap_source: "research-gaps+daily-info"
last_verified: "2026-07-25"
reviewed_date: "2026-07-25"
reviewed_by: "hermes-aiw-review-finalize-apply"
confidence: medium-high
sources:
  - "DeepResearch/2026-07-16-android17-oem-background-restriction.md"
last_body_apply_at: "2026-07-25T15:18:53+08:00"
last_body_apply_run_id: "20260725-151525-21e58a30"
last_body_apply_source: "source-index:16:DeepResearch/2026-07-16-android17-oem-background-restriction.md"
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_review_finalize_at: "2026-07-25T16:05:49+08:00"
last_review_finalize_run_id: "20260725-160531-5200f347"
---

# 25.25 OEM 厂商差异化后台限制与功耗诊断实战

<!-- outline-start -->
## 要点

### 🔹 AOSP 后台限制入口
- Android 17 的后台限制入口应从 `AppRestrictionController` 与 `BaseAppStateTracker` 体系切入，而不是从不存在的 `AppStateManager.java` 切入。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]
- `AppRestrictionController` 维护 tracker 链，材料核对到的 tracker 包括 `AppBatteryTracker`、`AppBatteryExemptionTracker`、`AppFGSTracker`、`AppMediaSessionTracker`、`AppPermissionTracker`、`AppBroadcastEventsTracker`、`AppBindServiceEventsTracker`。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

### 🔹 OEM 可干预边界
- OEM 可通过 `SystemConfig` 的 `bg-restriction-exemption` 配置后台限制豁免，`SystemConfig.java` 解析该标签后由 `AppRestrictionController` 读取豁免包集合。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]
- 系统豁免链至少覆盖系统模块、运营商特权应用、SystemConfig/DeviceConfig 豁免、DPC 保护/设备管理员和角色持有等来源。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

### 🔹 诊断切入点
- 先查限制等级，再查豁免来源，最后查 tracker 状态；材料给出的命令入口集中在 `cmd activity background get-restriction-level` 与 `dumpsys activity bg-restriction` / `dumpsys activity restriction` 系列。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]
- `/data/system/apprestriction/settings.xml` 是材料标注的后台限制设置持久化路径，可作为复现场景前后 diff 的候选证据点。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

<!-- outline-end -->

## 1. 本节边界：不要把 OEM 省电问题泛化成“厂商玄学”

面向 Android 17 / API 37 基线，厂商后台限制的系统排查应先落到 AOSP 已有的限制控制器、豁免链和 tracker 状态，而不是直接归因到某个 ROM 的私有策略。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 这并不否认厂商 ROM 会叠加私有冻结、清理、推送或自启动策略；本节只把已在 android-17.0.0_r1 材料中核过的一手源码边界写成诊断骨架。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

材料首先纠正了一个入口误判：android-17.0.0_r1 中没有 `AppStateManager.java`，后台限制核心入口是 `frameworks/base/services/core/java/com/android/server/am/AppRestrictionController.java`。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 因此，当遇到“同一个 App 在不同厂商设备后台行为差异很大”的问题时，AOSP 侧的第一层问题不是“哪个厂商杀了进程”，而是该 UID / package 当前处在哪个 restriction level、为什么得到这个 level、有没有系统豁免原因。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

## 2. AOSP 架构：`AppRestrictionController` + tracker 组合

`AppRestrictionController` 在材料中被描述为一个组合式控制器：它持有 `mAppStateTrackers`，并初始化多种 `BaseAppStateTracker` 子类来追踪应用状态。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 材料列出的 7 类 tracker 是：`AppBatteryTracker`、`AppBatteryExemptionTracker`、`AppFGSTracker`、`AppMediaSessionTracker`、`AppPermissionTracker`、`AppBroadcastEventsTracker`、`AppBindServiceEventsTracker`。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

```java
// 材料摘录：AppRestrictionController 初始化 tracker 链
mAppBatteryTracker = new AppBatteryTracker(mContext, controller);
mAppBatteryExemptionTracker = new AppBatteryExemptionTracker(mContext, controller);
mAppFGSTracker = new AppFGSTracker(mContext, controller);
mAppMediaSessionTracker = new AppMediaSessionTracker(mContext, controller);
mAppPermissionTracker = new AppPermissionTracker(mContext, controller);
controller.mAppStateTrackers.add(mAppBatteryTracker);
```

这个结构带来的实践含义是：后台限制不是单点开关，而是由电量、豁免、前台服务、媒体会话、权限、广播、绑定服务等多类状态共同影响。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 所以诊断报告里应同时记录 restriction level、豁免原因和 tracker 状态，避免只截一条 `dumpsys deviceidle` 就断言是 Doze 或 App Standby。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

## 3. OEM 接口边界：`SystemConfig` 的 `bg-restriction-exemption`

材料核到的明确 OEM / 系统配置入口是 `SystemConfig.java` 解析 `bg-restriction-exemption` 标签，并调用 `readBgRestrictionExemption(...)` 读取后台限制豁免配置。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

```java
// 材料摘录：SystemConfig.java 中解析豁免配置
case "bg-restriction-exemption":
    readBgRestrictionExemption(parser, permFile, allowOverrideAppRestrictions, name);
    break;
```

`AppRestrictionController` 随后通过 `SystemConfig.getInstance().getBgRestrictionExemption()` 获得豁免包集合，并在 debug 日志中打印 `bg-restriction-exemption: <package>`。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 对厂商差异化省电策略而言，这提供了一个可落地的核查点：如果某个系统应用、运营商应用或厂商核心组件“天然不受限制”，先确认它是否来自 SystemConfig 豁免，而不是把它当作普通三方应用对照组。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

```java
// 材料摘录：AppRestrictionController.java 获取豁免列表
private void initBgRestrictionExemptioFromSysConfig() {
    final SystemConfig sysConfig = SystemConfig.getInstance();
    mBgRestrictionExemptioFromSysConfig = sysConfig.getBgRestrictionExemption();
}
```

## 4. 多层级豁免链：先问“为什么没有被限制”

材料把 `getPotentialSystemExemptionReason()` 作为理解豁免来源的核心函数，并列出了从系统模块到角色持有的多层级判断。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 按材料给出的顺序，豁免来源至少包括：系统模块、运营商特权应用、`bg-restriction-exemption` / 运行时豁免包、DPC 保护应用、Active Device Admin、`ROLE_DIALER` / `ROLE_EMERGENCY` 等角色持有者。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

```java
// 材料摘录：getPotentialSystemExemptionReason() 的关键分支
if (isSystemModule(pkg)) {
    return REASON_SYSTEM_MODULE;
} else if (isCarrierApp(pkg)) {
    return REASON_CARRIER_PRIVILEGED_APP;
} else if (isExemptedFromSysConfig(pkg)) {
    return REASON_SYSTEM_ALLOW_LISTED;
} else if (mConstantsObserver.mBgRestrictionExemptedPackages.contains(pkg)) {
    return REASON_SYSTEM_ALLOW_LISTED;
} else if (pm.isPackageStateProtected(pkg, userId)) {
    return REASON_DPO_PROTECTED_APP;
} else if (appStandbyInternal.isActiveDeviceAdmin(pkg, userId)) {
    return REASON_ACTIVE_DEVICE_ADMIN;
}
```

排查时要把“被限制”和“被豁免”作为同一张表记录：普通应用可能因为进入 restricted bucket 或 background restricted level 而表现为后台任务延迟；系统或角色应用可能因为系统原因豁免而表现为对照组异常稳定。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 如果对照组本身命中系统模块、运营商特权应用或角色豁免，就不能用它来代表普通三方应用的后台可靠性。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

## 5. 豁免时间窗口：`AppBatteryExemptionTracker` 的 UID 共享状态

材料指出，`AppBatteryExemptionTracker` 继承自 `BaseAppStateDurationsTracker<AppBatteryExemptionPolicy, UidBatteryStates>`，用于处理豁免状态持续时间。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 在 `onStateChange(int uid, String packageName, boolean start, long now, int stateType)` 中，它按 UID 维护 `mUidPackageStates`，并在同 UID 下检查是否已有同类型豁免实例。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

```java
// 材料摘录：同 UID 下避免重复启动同类型豁免窗口
final SparseArray<ArrayMap<String, Integer>> map = mUidPackageStates.getMap();
ArrayMap<String, Integer> pkgsStates = map.get(uid);
if (start) {
    boolean alreadyStarted = false;
    for (int i = pkgsStates.size() - 1; i >= 0; i--) {
        final int s = pkgsStates.valueAt(i);
        if ((s & stateType) != 0) {
            alreadyStarted = true;
            break;
        }
    }
}
```

这段逻辑对复现有两个约束：第一，测试同 UID 多包或共享 UID 场景时，不能假设每个 package 都有完全独立的豁免窗口；第二，抓取日志时要同时记录 UID、packageName、stateType 和 start/stop 时间点。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 材料仍把 `UidBatteryStates` 中豁免窗口的实际计算公式列为待深入项，因此本节不进一步推导窗口长度或厂商可调参数。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

## 6. restriction level：把现象映射到等级

材料从 `ActivityManager.java` 摘录了 Android 17 的限制等级常量：`RESTRICTION_LEVEL_EXEMPTED = 20`、`RESTRICTION_LEVEL_ADAPTIVE_BUCKET = 30`、`RESTRICTION_LEVEL_RESTRICTED_BUCKET = 40`、`RESTRICTION_LEVEL_BACKGROUND_RESTRICTED = 50`、`RESTRICTION_LEVEL_FORCE_STOPPED = 60`。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 对应用侧现象而言，等级越高通常越接近“后台行为被系统强约束”的解释路径；但具体到 Job、Alarm、网络或进程生命周期，还需要结合对应子系统的 dumpsys 与日志证据，不能只凭等级单独下结论。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

```java
// 材料摘录：ActivityManager.java restriction level constants
public static final int RESTRICTION_LEVEL_EXEMPTED = 20;
public static final int RESTRICTION_LEVEL_ADAPTIVE_BUCKET = 30;
public static final int RESTRICTION_LEVEL_RESTRICTED_BUCKET = 40;
public static final int RESTRICTION_LEVEL_BACKGROUND_RESTRICTED = 50;
public static final int RESTRICTION_LEVEL_FORCE_STOPPED = 60;
```

AMS 侧通过 `noteAppRestrictionEnabled(...)` 把 package、uid、restrictionType、reason、subReason、source、threshold 等信息转交给 `AppRestrictionController.noteAppRestrictionEnabled(...)`。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 因此，排查模板里要保留 reason/subReason/source/threshold 字段，尤其是在厂商 ROM 增加自定义 source 或 subReason 时，这些字段比“是否被杀”更接近根因证据。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

## 7. 一键诊断命令：先 AOSP，后厂商私有

材料给出的 AOSP 侧诊断入口如下，可作为最小采样脚本的核心：[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

```bash
# 1) 查当前限制等级
adb shell cmd activity background get-restriction-level <package>

# 2) 查后台限制豁免列表 / 豁免状态
adb shell dumpsys activity bg-restriction exemption

# 3) 查某个 package 的 restriction 明细
adb shell dumpsys activity restriction <package>

# 4) 查某个 uid 的豁免原因
adb shell dumpsys activity bg-restriction exemption-reason <uid>

# 5) 查 tracker 状态
adb shell dumpsys activity restriction trackers
```

如果要区分 AOSP 行为与厂商私有行为，建议先固定同一套 AOSP 采样，再补充 ROM 私有 dumpsys / logcat 标签；否则容易把厂商私有输出当成系统通用结论。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 材料还标注 `/data/system/apprestriction/settings.xml` 为后台限制设置持久化路径，因此复现场景前后可以记录该文件是否发生变化，但读取该路径需要设备权限条件，不能假定普通 user build 一定可直接访问。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

## 8. 推荐问题单模板

记录 OEM 后台限制问题时，至少包含以下字段：[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

| 字段 | 记录内容 | 用途 |
|---|---|---|
| package / uid | 目标包名与 UID | 对齐 restriction、tracker 与豁免状态 |
| restriction level | `cmd activity background get-restriction-level` 输出 | 把现象映射到 AOSP 限制等级 |
| exemption reason | `dumpsys activity bg-restriction exemption-reason <uid>` 输出 | 判断是否命中系统模块、运营商、SystemConfig、DPC、角色等豁免 |
| tracker snapshot | `dumpsys activity restriction trackers` 输出 | 查看电量、豁免、FGS、媒体、权限、广播、绑定服务等 tracker 状态 |
| persistence diff | `/data/system/apprestriction/settings.xml` 前后差异（如可访问） | 判断限制设置是否持久化 |
| ROM 私有证据 | 厂商 dumpsys / logcat / 设置页截图 | 只作为厂商层补充，不替代 AOSP 基线 |

## 9. 待复查边界

材料明确列出若干未验证问题：不同 UID 下的豁免状态是否会影响厂商统一豁免策略、`UidBatteryStates` 中豁免窗口的实际计算公式、豁免判断顺序是否可被厂商调整、持久化 XML 的具体厂商自定义字段、从 `ADAPTIVE_BUCKET` 到 `EXEMPTED` 的触发条件。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md] 这些问题在本节只作为复查清单，不写成确定性结论。[来源: DeepResearch/2026-07-16-android17-oem-background-restriction.md]

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]
[缺口来源: intake/research-gaps.md — "厂商差异化省电策略的系统排查指南" — 重要程度：高]
