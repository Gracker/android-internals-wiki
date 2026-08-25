---
title: Android 17 移动数据配额与 Data Saver 执行链路
chapter: '24.11'
section: '24.11'
status: finalized
applicable_versions: Android 10 (API 29) - Android 17 (API 37)
tags:
- network
- io
- http
last_draft_polish_at: '2026-08-08T15:36:16+08:00'
last_draft_polish_run_id: 20260808-153552-draft-polish-43dea43a
last_rework_at: '2026-07-30T13:35:29+08:00'
last_rework_run_id: 20260730-133529-rework-43dea43a
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
last_verified: '2026-08-15'
last_verified_against: Android android-17.0.0_r1 / kernel android17-6.18-2026-06_r6 / Android Developers Data Saver, NetworkCapabilities, NetworkStatsManager and WorkManager references 2026-08; verified Android TV Data Saver exception and no Android 18/API 38+ conclusions.
last_review_finalize_at: '2026-08-08T16:07:26+08:00'
last_review_finalize_run_id: 20260808-160556-bac29a37
confidence: high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service-t/src/com/android/server/net/NetworkStatsService.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service-t/src/com/android/server/net/NetworkStatsFactory.java
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/BpfNetMaps.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/net/NetworkPolicyManagerService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/net/NetworkManagementService.java
- type: aosp
  path: https://android.googlesource.com/platform/system/netd/+/refs/tags/android-17.0.0_r1/server/NetdNativeService.cpp
- type: aosp
  path: https://android.googlesource.com/platform/system/netd/+/refs/tags/android-17.0.0_r1/server/BandwidthController.cpp
- type: aosp
  path: https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service-t/jni/com_android_server_net_NetworkStatsFactory.cpp
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/netfilter/xt_quota2.c
- type: official
  path: https://developer.android.com/reference/android/net/ConnectivityManager
- type: official
  path: https://developer.android.com/reference/android/net/NetworkCapabilities
- type: official
  path: https://developer.android.com/reference/android/app/usage/NetworkStatsManager
- type: official
  path: https://developer.android.com/develop/connectivity/network-ops/data-saver
- type: official
  path: https://developer.android.com/reference/androidx/work/NetworkType
- type: official
  path: https://developer.android.com/reference/android/app/job/JobInfo
---

# Android 17 移动数据配额与 Data Saver 执行链路

Android 17 的网络用量控制包含统计、周期策略、告警、阻断和后台访问限制。源码里的配额（quota）表示剩余字节预算，耗尽后拒绝网络报文；它不表示把移动网络调整到某个每秒千比特（Kbit/s）速率。`NetworkStatsService` 负责网络用量统计，`NetworkPolicyManagerService` 负责把套餐周期策略转换为系统规则。本节沿 `android-17.0.0_r1` 追踪调用路径，并说明普通应用能够观察和控制的边界。

## 1. 版本与结论

- 平台源码锚点：Android 17（API 37），标签 `android-17.0.0_r1`。
- 内核源码锚点：`android17-6.18-2026-06_r6`。
- `NetworkStatsService` 已位于 Connectivity Mainline 模块。Mainline 是可通过系统组件更新机制独立升级的 Android 模块，它不再使用旧的 `frameworks/base/services/core/...` 路径。
- `NetworkPolicyManagerService` 仍位于 `frameworks/base`，运行在承载 Android 核心服务的 `system_server` 进程中。
- 接口配额由 `NetworkPolicyManagerService` 计算剩余字节，经 `NetworkManagementService` 和原生网络守护进程 `netd` 写入 `quota2` 规则。Netfilter 是 Linux 内核的报文过滤框架，`quota2` 是其中按报文字节递减计数的匹配器。
- 周期总量超过强制上限且未延后提醒时，Android 的电话与移动网络框架还会通过 `TelephonyManager.setPolicyDataEnabled(false)` 停用策略数据。
- 在本节追踪的手机移动数据路径中，流量节省程序（Data Saver）和应用用户标识符（UID）规则控制某个应用能否在计量网络传输，不提供速率整形。Android TV 是官方明确记录的例外，会对前台和后台流量设置不同速率。

这几条路径共享统计结果，却有不同的触发条件和执行对象。排查问题时要先确认关注的是用量记录、阈值提醒、接口总量限制，还是 UID 后台访问限制。

## 2. 五类容易混淆的配额概念

| 名称 | 计算或保存位置 | 作用 | 是否限速 |
| --- | --- | --- | --- |
| 历史网络用量 | `NetworkStatsService`、`NetworkStatsRecorder` | 保存接口、UID、标签维度的字节和报文统计 | 否 |
| `NetworkPolicy.warningBytes` | `NetworkPolicyManagerService` | 触发用量提醒并调整采集时机 | 否 |
| `NetworkPolicy.limitBytes` | `NetworkPolicyManagerService`、`netd`、`quota2` | 计算接口剩余字节；耗尽后拒绝报文，并可停用移动数据 | 否，属于总量限制 |
| Data Saver / UID 规则 | `NetworkPolicyManagerService`、Connectivity、BPF/防火墙规则 | 限制后台 UID 使用计量网络，处理前台和允许名单例外 | 手机路径为访问控制；Android TV 另有速率限制 |
| 机会型配额（opportunistic quota） | `NetworkPolicyManagerService` | 为可等待的作业、多路径传输等流量给出预算 | 否，与用户套餐强制上限无关 |

UID 是 Android 基于 Linux 用户标识符为应用分配的隔离身份。BPF（Berkeley Packet Filter）在这里指内核中执行的网络统计与规则程序，以及供系统服务读写的映射表。`NetworkStatsFactory` 还有名为 `per_uid_tag_throttling` 的配置，它限制单个 UID 可进入统计结果的不同流量标签数量，防止标签种类持续增加。这里的 `throttling` 只限制统计标签数量，不会降低网络吞吐。

## 3. Android 17 中各模块的职责

虚拟专用网络（VPN）会改变流量归因；464xlat 是让 IPv4 应用通过仅支持 IPv6 的网络通信的地址转换机制。带着这两个边界查看模块职责，才能理解接口总量与应用 UID 总量为何可能不同。

| 层次 | Android 17 源码 | 职责 |
| --- | --- | --- |
| 统计服务 | [`NetworkStatsService.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service-t/src/com/android/server/net/NetworkStatsService.java) | 轮询计数器、处理网络身份、记录历史、服务查询和用量回调 |
| 统计读取 | [`NetworkStatsFactory.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service-t/src/com/android/server/net/NetworkStatsFactory.java) | 切换活动 BPF 统计表，读取接口与 UID 统计，处理 VPN 和 464xlat 归因 |
| BPF 规则入口 | [`BpfNetMaps.java`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service/src/com/android/server/BpfNetMaps.java) | 管理统计表选择、UID 所有者规则和 Data Saver 开关 |
| 周期策略 | [`NetworkPolicyManagerService.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/net/NetworkPolicyManagerService.java) | 匹配网络策略，计算警告/上限余量，更新通知、接口规则和 UID 规则 |
| Java 到 `netd` | [`NetworkManagementService.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/net/NetworkManagementService.java) | 校验权限和接口状态，通过 Binder 跨进程调用接口 `INetd` 调用原生服务 |
| 原生执行 | [`NetdNativeService.cpp`](https://android.googlesource.com/platform/system/netd/+/refs/tags/android-17.0.0_r1/server/NetdNativeService.cpp)、[`BandwidthController.cpp`](https://android.googlesource.com/platform/system/netd/+/refs/tags/android-17.0.0_r1/server/BandwidthController.cpp) | 安装、更新和移除接口 `quota2` 规则 |
| 内核匹配器 | [`xt_quota2.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/net/netfilter/xt_quota2.c) | 按报文字节递减命名计数器，跨越阈值时发出事件 |

模块位置也会影响源码检索。沿旧版路径 `frameworks/base/services/core/java/com/android/server/net/NetworkStatsService.java` 查找 Android 17 会得到错误结论，因为这一服务的实现已经进入 `packages/modules/Connectivity/service-t`。

## 4. 统计路径：BPF 计数如何进入历史记录

### 4.1 UID 明细使用双表切换

`NetworkStatsFactory.readNetworkStatsDetail()` 在持有自身数据锁时调用 `BpfNetMaps.swapActiveStatsMap()`。`BpfNetMaps` 修改 `CURRENT_STATS_MAP_CONFIGURATION_KEY`，在 A/B 两张统计表之间切换。A/B 表是交替承担写入与读取的两份映射：BPF 程序观察到新配置后改写活动表，服务则读取已经停止增长的非活动表，从而获得相对稳定的增量。

读取结果是自上次切换以来的增量。`NetworkStatsFactory` 把增量合入 `mPersistSnapshot`，再按顺序处理 464xlat 修正和 VPN TUN 流量归因。TUN 是 VPN 常用的虚拟网络接口。查询方获得的是筛选后的累计视图，并非直接读取一张持续增长的 UID 表。

接口汇总走另一条入口：`readNetworkStatsSummaryXt()` 调用 `getNetworkStatsDev()` 读取设备和接口维度统计。Java 原生接口（Java Native Interface，JNI）实现 [`com_android_server_net_NetworkStatsFactory.cpp`](https://android.googlesource.com/platform/packages/modules/Connectivity/+/refs/tags/android-17.0.0_r1/service-t/jni/com_android_server_net_NetworkStatsFactory.cpp)，通过 `BpfNetworkStats` 解析接口和 UID 明细，并填充 `uid`、前后台集合 `set`、流量分类标签 `tag`、收发字节与报文数。

### 4.2 `NetworkStatsService` 先读 UID，再读接口

`NetworkStatsService.recordSnapshotLocked()` 明确规定读取顺序：

1. `getNetworkStatsUidDetail(INTERFACES_ALL)` 取得 UID 明细。
2. `readNetworkStatsSummaryXt()` 取得接口汇总。
3. 合并自定义统计提供方 `NetworkStatsProvider` 补充的接口统计。
4. `mXtRecorder` 记录接口历史。
5. `mUidRecorder` 和 `mUidTagRecorder` 记录 UID、标签历史。
6. 通知用量观察器检查已注册的阈值。

UID 统计先读，是为了减少接口统计相对 UID 统计多计一小段时间窗口的概率。两次读取仍不具备数据库事务的原子性；网络身份切换、VPN、网络共享和硬件卸载都会让统计归因需要额外处理。这里的硬件卸载是把部分网络处理交给网卡或专用硬件，系统需要把相应计数合回统一视图。

`performPollLocked()` 在周期闹钟、网络状态变化、强制更新、UID 移除和全局告警等场景执行。它先向自定义统计提供方发起轮询，再记录快照，并按照调用标志决定是否写入持久化历史。自定义 `NetworkStatsProvider` 是系统组件向统计服务补充硬件或专用网络计数的接口。

### 4.3 全局告警负责促使系统及时轮询

`NetworkStatsService.registerGlobalAlert()` 调用 `INetd.bandwidthSetGlobalAlert()`，同时把阈值发给已注册的统计提供方。内核命名计数器耗尽后，`AlertObserver.onQuotaLimitReached()` 针对 `globalAlert` 安排一次延迟轮询，轮询完成后重新注册全局告警。

全局告警的用途是促使系统及时刷新统计数据。它不会替代某个套餐周期的 `warningBytes` 或 `limitBytes`，也不会单独关闭网络。

## 5. 周期策略如何变成接口剩余字节

`NetworkPolicyManagerService` 用 `NetworkTemplate` 作为策略键。`NetworkTemplate` 是描述移动订阅、运营商或指定网络匹配条件的模板；当前连接快照 `NetworkStateSnapshot` 会转换成用于策略匹配的 `NetworkIdentity`。

内部方法名的 `AL`、`NL` 或 `UL` 后缀用于标记调用时应持有的服务锁，不是公开 API 的行为模式。`handleNetworkPoliciesUpdateAL()` 的顺序是：

1. 按需规范化策略。
2. `updateNetworkEnabledNL()` 判断是否应启用匹配的网络。
3. `updateNetworkRulesNL()` 计算并下发接口规则。
4. `updateNotificationsNL()` 刷新用量通知。
5. 把策略写入持久化文件。

这段 Android 17 源码展示了强制上限和警告余量的计算，关键变量是 `totalBytes`、周期起点和延后处理时间：

```java
final long totalBytes = getTotalBytes(policy.template, start, end);

if (hasLimit && policy.lastLimitSnooze < start) {
    limitBytes = Math.max(1, policy.limitBytes - totalBytes);
}

if (hasWarning && policy.lastWarningSnooze < start
        && !policy.isOverWarning(totalBytes)) {
    warningBytes = Math.max(1, policy.warningBytes - totalBytes);
}
```

这里下发的是从当前用量到阈值还剩多少字节。内核规则不接受 0 字节，所以余量用 `Math.max(1, ...)` 保持至少 1；服务随后还会根据完整周期统计停用移动数据。源码中的 `snooze` 表示用户暂时延后警告或强制上限。它只在当前周期内影响对应阈值；进入新周期后，旧的延后时间早于新周期起点，限制重新生效。

### 5.1 计量接口没有套餐上限，也会安装规则入口

计量网络（metered network）表示传输可能计入用户套餐或产生费用。`updateNetworkRulesNL()` 对满足警告、强制上限或 `policy.metered` 任一条件的接口调用 `setInterfaceQuotasAsync()`。没有有效周期、没有强制上限或已延后提醒时，余量可为 `Long.MAX_VALUE`。

Android 17 还会为没有显式 `NetworkPolicy` 的计量接口下发 `Long.MAX_VALUE`。这个接近 64 位有符号整数上限的值，为计量接口安装规则入口，使 Data Saver 和 UID 计量网络限制有执行位置；它表示接口总量近似不受限，不代表该网络免费。

同一策略同时匹配多个接口时，源码会记录 `shared quota unsupported; generating rule for each iface`，表示当前实现不支持跨接口共享同一内核配额。每个接口各自获得一份相同余量，所以不能把多个接口的内核计数器相加视作共享套餐的精确强制限制。策略服务仍以模板历史总量判断周期是否超限。

### 5.2 警告值不会进入接口拒绝规则

处理 `MSG_UPDATE_INTERFACE_QUOTAS` 时，服务执行三件事：

- 移除接口旧上限；
- 调用 `setInterfaceLimit(iface, limit)` 安装新上限；
- 调用 `NetworkStatsService.setStatsProviderWarningAndLimitAsync()`，把警告和上限告知自定义统计提供方。

`setInterfaceLimit()` 只把 `limitBytes` 传给 `NetworkManagementService.setInterfaceQuota()`。警告值用于提醒和统计提供方回调，平台通过轮询后的周期总量更新通知。文档或监控中的 `warning` 字段应解释为提醒阈值，不能写成内核拒绝流量的阈值。

## 6. 接口上限如何进入 `netd` 与内核

`NetworkManagementService.setInterfaceQuota()` 需要仅系统网络组件持有的 Network Stack 特权。它拒绝给同一接口重复安装未移除的上限，随后调用 `INetd.bandwidthSetInterfaceQuota(iface, quotaBytes)`。`NetdNativeService` 再把请求交给 `BandwidthController.setInterfaceQuota()`。

末尾的 `REJECT` 决定了这项接口上限的执行语义：

```cpp
const std::string chain = "bw_costly_" + iface;

StringPrintf("-A %s -j bw_penalty_box", chain.c_str());
StringPrintf("-I bw_INPUT %d -i %s -j %s", ruleInsertPos, iface.c_str(), chain.c_str());
StringPrintf("-I bw_OUTPUT %d -o %s -j %s", ruleInsertPos, iface.c_str(), chain.c_str());
StringPrintf("-A %s -m quota2 ! --quota %" PRId64
             " --name %s -j REJECT",
             chain.c_str(), maxBytes, cost.c_str());
```

`bw_costly_<iface>` 同时挂到输入、输出和转发路径。`quota2` 计数器按报文长度递减；`! --quota` 使匹配结果在余量耗尽后成立，后续目标是 `REJECT`。这是一条按总字节数触发的拒绝规则。它没有令牌桶、队列调度或目标速率参数；令牌桶是按固定速率补充发送额度、从而控制吞吐的常见整形算法。

同一命名计数器可由 `/proc/net/xt_quota/<name>` 更新。`/proc` 是内核向用户空间暴露运行状态和控制入口的虚拟文件系统。`BandwidthController.updateQuota()` 会向该路径写入新值；内核 `xt_quota2.c` 在计数器从非零跨到零时记录事件，`netd` 再把 `onQuotaLimitReached(alertName, ifName)` 传给 `NetworkManagementService` 的观察器。

`NetworkPolicyManagerService` 收到接口上限事件后会：

1. 确认该接口仍属于当前计量接口集合。
2. 强制 `NetworkStatsService` 更新统计。
3. 重新计算接口规则。
4. 重新判断网络是否启用。
5. 更新通知。

触发事件只说明某个内核计数器到达阈值。策略判断仍使用强制刷新后的模板周期总量，避免仅凭一次接口事件决定用户套餐状态。

## 7. 超过强制上限后，移动数据还会被策略关闭

`updateNetworkEnabledNL()` 对每个带周期和强制上限的策略查询当前周期总量。当 `policy.isOverLimit(totalBytes)` 成立，且 `lastLimitSnooze` 早于周期起点，匹配网络会被标记为禁用。

移动网络和运营商模板进入 `setNetworkTemplateEnabledInner()` 后，服务查出匹配订阅，逐个执行：

```java
tm.createForSubscriptionId(subId).setPolicyDataEnabled(enabled);
```

Telephony 是 Android 的电话与移动网络框架。这段调用在套餐强制上限成立时改变其策略数据开关，不设置无线连接速率。用户延后限制或进入新周期后，重新计算会把 `enabled` 改回 `true`。

接口 `quota2` 的即时拒绝和 Telephony 策略开关互相补充：前者在剩余字节耗尽时阻止继续传输，后者按模板周期总量控制移动数据连接。VPN、叠加接口和多接口场景中，两者观察的对象并不完全相同。

## 8. Data Saver 与 UID 计量网络规则

Data Saver 的全局状态由 `NetworkPolicyManagerService.setRestrictBackgroundUL()` 更新。服务先重新计算 UID 规则，再调用 `NetworkManagementService.setDataSaverModeEnabled()`。Android 17 的 `NetworkManagementService` 转到 `ConnectivityManager.setDataSaverEnabled()`；Connectivity 服务同时更新 `netd.bandwidthEnableDataSaver()` 和 `BpfNetMaps.setDataSaverEnabled()`。

对单个 UID，`updateRulesForDataUsageRestrictionsULInner()` 计算两组原因：

- 阻止原因：设备管理员限制、Data Saver、用户设置的计量网络后台限制；
- 允许原因：系统 UID、前台 UID、用户允许名单。

启用新的计量防火墙规则组时，服务使用 `FIREWALL_CHAIN_METERED_DENY_ADMIN`、`FIREWALL_CHAIN_METERED_DENY_USER` 和 `FIREWALL_CHAIN_METERED_ALLOW`。兼容路径则更新计量网络允许或拒绝名单。`BpfNetMaps.setUidRule()` 把规则转换成 UID 所有者位标记，也就是用整数中的不同二进制位记录多种规则；`isUidNetworkingBlocked(uid, isNetworkMetered)` 结合计量属性、UID 规则和 Data Saver 开关给出阻止结果。

在手机移动数据路径中，Data Saver 主要限制后台 UID，前台活动、系统 UID 和用户允许名单会改变有效结果。因此，Data Saver 已开启不能直接推出该应用的全部网络请求都会失败。[官方 Data Saver 指南](https://developer.android.com/develop/connectivity/network-ops/data-saver) 另行说明，Android TV 会把前台应用限制到 800 Kbit/s、后台应用限制到 10 Kbit/s；排查 TV 时不能套用手机路径的无速率整形结论。

## 9. 普通应用能够使用的公开接口

普通第三方应用没有 `MANAGE_NETWORK_POLICY`、`NETWORK_SETTINGS` 或 Network Stack 等系统特权，不能调用 `setInterfaceQuota()`、修改平台 `NetworkPolicy`，也不能控制 `setPolicyDataEnabled()`。应用侧应围绕网络属性、Data Saver 状态、任务约束和自身统计设计行为。

### 9.1 观察 Data Saver

`ConnectivityManager.getRestrictBackgroundStatus()` 返回：

- `RESTRICT_BACKGROUND_STATUS_DISABLED`：全局后台数据限制关闭；
- `RESTRICT_BACKGROUND_STATUS_WHITELISTED`：限制开启，但当前应用位于允许名单；
- `RESTRICT_BACKGROUND_STATUS_ENABLED`：当前应用在后台受限制。

变化通知使用 `ConnectivityManager.ACTION_RESTRICT_BACKGROUND_CHANGED`。系统只把这条广播发送给运行时通过 `registerReceiver()` 动态注册的接收器，清单中的静态接收器收不到。接收广播后仍要再次调用 `getRestrictBackgroundStatus()`，因为广播本身不携带可直接采用的新状态。

具体行为见 [Data Saver 指南](https://developer.android.com/develop/connectivity/network-ops/data-saver) 和 [`ConnectivityManager`](https://developer.android.com/reference/android/net/ConnectivityManager)。

### 9.2 判断当前网络是否计量

`ConnectivityManager.isActiveNetworkMetered()` 适合取得当前默认网络的即时判断。需要持续跟踪时，应注册异步网络回调 `NetworkCallback` 并读取最新 `NetworkCapabilities`；具有 `NET_CAPABILITY_NOT_METERED` 的网络视为非计量网络。网络能力可能在连接存续期间变化，长下载不能只在开始时判断一次。

`NET_CAPABILITY_TEMPORARILY_NOT_METERED` 表示通常计量的网络暂时不计量。AndroidX 持久化后台任务库 WorkManager 对应 `NetworkType.TEMPORARILY_UNMETERED`。该能力可随时消失；消失后，工作单元需要停止不应继续消耗计量流量的传输。

### 9.3 查询历史用量

[`NetworkStatsManager`](https://developer.android.com/reference/android/app/usage/NetworkStatsManager) 返回按时间桶保存的历史统计。时间桶是把一段连续时间内的字节数聚合为一条记录。Android 7.0 及以上，应用默认可查询自己的用量；设备汇总或其他应用用量需要声明 `PACKAGE_USAGE_STATS`，并由用户在设置中授予使用情况访问权。设备所有者、资料所有者和具备运营商权限的应用另有授权范围。

这些查询可能耗时数秒，应放在工作线程。统计桶通常以小时为量级，API 文档也明确说明明细查询不会对只覆盖部分时间范围的桶做比例估算。它适合用量分析，不适合实时测速，也不能代替运营商账单。

### 9.4 调度大流量工作

这段 WorkManager 约束让大文件同步只在非计量网络上运行：

```kotlin
val constraints = Constraints.Builder()
    .setRequiredNetworkType(NetworkType.UNMETERED)
    .build()

val request = OneTimeWorkRequestBuilder<LargeSyncWorker>()
    .setConstraints(constraints)
    .build()
```

调度器会在约束不满足时停止当前工作并等待条件恢复。应用仍应在传输边界保存进度并支持取消，因为网络能力可在任务执行期间变化。`CONNECTED` 只要求存在可用网络，不代表该网络不计量。

## 10. 诊断与验证

Android 调试桥（Android Debug Bridge，ADB）的 `dumpsys` 命令可读取系统服务诊断信息。这组命令用于检查策略、统计和 Java 到 `netd` 的状态；`--poll` 会要求系统刷新统计，不应在高频采样循环中反复执行：

```shell
adb shell dumpsys netpolicy
adb shell dumpsys netstats --poll
adb shell dumpsys network_management
```

`dumpsys netpolicy` 适合核对周期、警告阈值 `warning`、强制上限 `limit`、延后状态 `snooze`、计量接口和 UID 规则；`dumpsys netstats --poll` 适合确认接口与 UID 历史是否刷新；`dumpsys network_management` 可检查活动接口配额、告警和 Data Saver 状态。面向普通用户的 `user` 构建可能隐藏部分原生规则和 BPF 表内容，命令没有输出不能证明规则不存在。

测试应用的 Data Saver 行为时，可以使用 Android 官方指南给出的 `cmd netpolicy`：

```shell
adb shell cmd netpolicy set restrict-background true
adb shell cmd netpolicy add restrict-background-whitelist <UID>
adb shell cmd netpolicy remove restrict-background-whitelist <UID>
adb shell cmd netpolicy set restrict-background false
```

这些命令会修改设备状态。测试完成后应恢复 Data Saver 开关，并移除为测试加入的 UID。应用进程要覆盖前台、后台、允许名单三种状态；只验证开关打开时请求失败，无法说明规则是否正确。

平台或设备厂商验证还应覆盖：

| 场景 | 观察点 |
| --- | --- |
| 警告阈值（`warning`）前后 | 通知是否按周期总量出现；接口流量不应因警告阈值被拒绝 |
| 强制上限（`limit`）前后 | `quota2` 事件、强制统计刷新、接口拒绝与移动数据策略开关 |
| 延后处理（`snooze`） | 当前周期强制限制是否解除；下一周期是否恢复 |
| VPN / 464xlat | UID 归因与接口总量差异是否符合预期 |
| 多接口匹配同一模板 | 每接口余量规则与模板总量判断是否产生可解释差异 |
| Data Saver | 后台 UID、前台 UID、用户允许名单是否得到不同结果 |
| 自定义统计提供方 | `warning` / `limit` 回调与平台轮询后的数据是否一致 |

这组用例应同时记录设备形态、模板周期、接口和 UID，才能把 Android TV 的速率限制、接口配额耗尽后的拒绝，以及 UID 后台访问限制分开。只记录网络不可用这一结果，无法确定执行规则位于哪一层。

## 11. 排查时的判断顺序

遇到移动数据速度变慢一类反馈，可按这个顺序定位：

1. 先确认设备是否为 Android TV。TV 的 Data Saver 可能直接限制速率；手机套餐配额对应连接被拒绝或移动数据被停用。
2. 检查当前网络是否计量，以及应用处于前台、后台还是允许名单。
3. 在 `dumpsys netpolicy` 中确认匹配模板、周期、`warning`、`limit` 和 `snooze`。
4. 强制刷新 `netstats`，比较模板总量、接口总量和 UID 总量，记录 VPN、共享网络与订阅切换。
5. 在有权限的调试构建上检查 `NetworkManagementService`、`netd` 和 `xt_quota2` 命名计数器，确认余量规则是否安装到预期接口。
6. 运营商账单与系统统计不一致时，分别检查计费口径、时间区间、零费流量、共享套餐和漫游；Android 统计值不能作为运营商结算值的替代品。

## 全文小结

Android 17 的手机移动数据机制可以概括为：BPF 负责计数和 UID 规则判定，`NetworkStatsService` 保存可查询的历史，`NetworkPolicyManagerService` 用周期策略计算余量，`netd` 与 `xt_quota2` 执行接口总量限制，Telephony 处理移动数据策略开关。把这几层分开，才能判断现象来自统计延迟、提醒、访问控制，还是套餐强制上限；Android TV 的 Data Saver 速率限制需要单独判断。
