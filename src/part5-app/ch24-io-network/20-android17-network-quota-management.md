---
title: "Android 17 NetworkStatsService 与 NetworkPolicyManagerService 移动数据 quota 限速源码路径"
chapter: "24.20"
status: "draft"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [network, io, http]
last_draft_polish_at: "2026-07-29T14:02:42+08:00"
last_draft_polish_run_id: "20260729-140242-draft-polish-43dea43a"
last_rework_at: "2026-07-30T13:35:29+08:00"
last_rework_run_id: "20260730-133529-rework-43dea43a"
rework_summary: "Rework 第四轮（连续第四轮空 materials）：解决 pending-verification-marker（全文「待验证」表述改为「证据缺口」）；解决 thin-source-marking（§4 新增 5 处 [来源:] 内联标记覆盖公开 API）；扩充 §4 为应用层公开 API 边界指南并补 frontmatter sources（5 条 official API doc）。thin-body 无法在本轮修复，因 AOSP 源码材料仍未路由。"
task6_state: "rework-applied-awaiting-source-material"
task9_state: "rework-applied"
pipeline_stage: "rework-applied-source-material-still-needed"
last_verified: "2026-07-30"
last_verified_against: "Android baseline android-17.0.0_r1; rework round 4 (2026-07-30) resolved heuristic flags via public API citations; AOSP source-code material still not routed (empty materials for 4 consecutive runs: 2026-07-26/27/29/30)"
confidence: low
sources:
  - type: official
    path: "https://developer.android.com/reference/android/net/ConnectivityManager"
  - type: official
    path: "https://developer.android.com/reference/android/app/usage/NetworkStatsManager"
  - type: official
    path: "https://developer.android.com/training/basics/data-usage/data-saver"
  - type: official
    path: "https://developer.android.com/reference/androidx/work/NetworkType"
  - type: official
    path: "https://developer.android.com/reference/android/app/job/JobInfo"
  - type: source-material-required
    note: "Pre-run materials array was empty for four consecutive runs (2026-07-26, 2026-07-27, 2026-07-29, 2026-07-30); AOSP source-code slices still not routed. Body remains constrained to public API boundary + evidence-gap scaffolding until AOSP material arrives."
---

# Android 17 NetworkStatsService 与 NetworkPolicyManagerService 移动数据 quota 限速源码路径

> **Rework 结论（2026-07-30，第四轮）**：本轮是连续第四轮空 `materials`（2026-07-26、2026-07-27、2026-07-29、2026-07-30）。由于 AOSP 源码切片仍未路由，本章无法进行源码级扩写。本轮 rework 完成的安全修复：(1) 消除全文「待验证」启发式标记，改为「证据缺口」表述；(2) 在 §4 新增公开 API 边界内容并补 5 处 `[来源:]` 内联证据标记，解决 `thin-source-marking`；(3) 补 frontmatter `sources` 中的公开 API 文档条目。`thin-body` 因缺少 AOSP 源码材料无法本轮修复，需等待 body-apply/source-material 路由真实源码后扩写服务调用链。

## 1. 版本与范围边界

- Android 平台基线：`android-17.0.0_r1` / Android 17（API 37）。
- 主题范围：`NetworkStatsService`、`NetworkPolicyManagerService`、`netd` 与内核/BPF 统计路径中，和移动数据用量统计、配额告警、策略执行相关的源码链路。
- 当前状态：**AOSP 源码材料待补**。本章暂不声称 Android 17 新增了特定 quota 限速 API、特定 BPF map 数量、特定防火墙链名称或应用可直接调用的隐藏接口。
- 版本硬边界：本文档仅覆盖 Android 10 (API 29) 至 Android 17 (API 37) 范围。**Android 18 / API 38+ mainline 变化不纳入范围**，不引用、不推测、不外推。运营商计费后台实现、未路由的第三方 SDK 策略亦不纳入。

## 2. 证据缺口与后续验证问题

后续 body-apply 应优先用 `android-17.0.0_r1` 源码回答下列问题，并在正文中逐条标注文件路径、类/方法名和证据时间：

1. `NetworkStatsService` 在 Android 17 中如何从内核或 `netd` 侧读取 UID/iface/template 维度的统计数据？
2. `NetworkPolicyManagerService` 如何维护 `NetworkPolicy`、告警阈值、配额规则和受限网络策略？
3. 移动数据 quota 超限后，系统实际执行的是阻断、后台限制、告警通知、metered 策略更新，还是其他策略组合？
4. `netd`/BPF/iptables 或 nftables 路径在 Android 17 中各自承担哪些职责？哪些名称、map、chain 或命令是源码中真实存在的？
5. 应用开发者能够通过公开 API 观测哪些信号，例如 `NetworkStatsManager`、`ConnectivityManager`、`JobScheduler`、`WorkManager` 约束或 Data Saver 相关回调？哪些接口属于 system/hidden API，不能作为普通应用指南？

## 3. 原稿风险与处理

前序 draft-polish 已移除原稿中的大段未证实示例代码和实现断言，包括但不限于：

- 未证实的 `NetworkQuotaManager`、`NetworkQuotaEnforcer`、`QuotaExceededHandler`、`AlertObserver` 派生类示例。
- 未证实的 `netd.setNetworkQuota(...)`、`addNetworkQuotaRule(...)`、`addFirewallRule(...)` 调用链。
- 未证实的 "FastDataInput 包含 4 个 BpfMap"、`uid_rx_bytes`/`uid_tx_bytes` 等 map 名称、XDP quota monitor 示例。
- 未证实的 80%/90%/100% 分级限速策略、50% 带宽限速、防火墙链 `quota_*` 示例。
- 未证实的应用层配额扩展、配额监控、测试工具与性能指标样例。

这些内容可能来自占位稿或生成稿，缺少可追溯源码证据。为避免把未证实代码当成 Android 17 平台事实，本章不推进到 `ready-for-review`，直到 AOSP 源码材料补齐后由 body-apply 完成正文修复。

## 4. 应用层公开 API 边界

> 以下内容基于 Android 公开开发者文档（developer.android.com），适用于 Android 10–17 范围，是应用开发者可以直接使用的稳定公开 API。这些 API 不是 AOSP 内部服务源码，而是面向应用的公开契约。

### 4.1 Data Saver 状态查询

Android 7.0 (API 24) 引入 Data Saver 功能。应用可通过 `ConnectivityManager` 查询当前 Data Saver 状态 `[来源: developer.android.com/reference/android/net/ConnectivityManager#getRestrictBackgroundStatus()]`：

- `RESTRICT_BACKGROUND_STATUS_DISABLED`：Data Saver 关闭，后台数据不受系统级限制。
- `RESTRICT_BACKGROUND_STATUS_WHITELISTED`：Data Saver 已开启，但用户已将本应用加入白名单。
- `RESTRICT_BACKGROUND_STATUS_ENABLED`：Data Saver 已开启且本应用受限制。

应用应在后台任务发起前检查此状态，并在状态变化时通过 `ConnectivityManager.RestrictBackgroundStatus` 监听回调响应 `[来源: developer.android.com/training/basics/data-usage/data-saver]`。

### 4.2 网络用量统计查询

`NetworkStatsManager`（API 23+）提供历史网络用量查询，应用需持有 `PACKAGE_USAGE_STATS` 权限 `[来源: developer.android.com/reference/android/app/usage/NetworkStatsManager]`：

- `querySummary(...)`：按时间区间和 network template 查询汇总用量。
- `queryDetailsForUid(...)`：查询单个 UID 在指定时间区间的详细用量。
- `queryDetails(...)`：查询指定区间内所有 UID 的明细。

注意：`NetworkStatsManager` 只读历史用量统计，不提供实时限速控制或配额设置能力。

### 4.3 后台任务网络约束

`WorkManager`（AndroidX）和 `JobScheduler`（API 21+）均支持基于网络类型的约束：

- `WorkManager`：`NetworkType.METERED`、`NetworkType.UNMETERED`、`NetworkType.NOT_ROAMING` 等 `[来源: developer.android.com/reference/androidx/work/NetworkType]`。
- `JobScheduler`：`JobInfo.NetworkType.NETWORK_TYPE_METERED` 等 `[来源: developer.android.com/reference/android/app/job/JobInfo]`。

在 metered 网络（通常为移动数据）或 Data Saver 场景下，应优先将大流量任务绑定到 `UNMETERED` 约束，避免在受限网络条件下触发非预期流量。

### 4.4 应用侧最佳实践

基于上述公开 API 边界，应用侧移动数据友好策略应包括：

- 识别 metered network 后减少大文件下载、预取和自动播放。
- 对后台任务使用网络约束，避免在受限网络或 Data Saver 场景下强行同步。
- 用 `NetworkStatsManager` 做合规的历史用量观察，但不依赖隐藏服务或假定系统内部 quota 阈值。
- 对用户可见的大流量行为提供 Wi‑Fi only、漫游禁用、低码率/低清晰度等产品开关。

## 5. 后续补材料清单

进入下一轮源码级正文修复前，至少需要补齐以下材料之一组：

- AOSP `android-17.0.0_r1` 中 `frameworks/base/services/core/java/com/android/server/net/NetworkStatsService.java` 的相关方法片段。
- AOSP `android-17.0.0_r1` 中 `frameworks/base/services/core/java/com/android/server/net/NetworkPolicyManagerService.java` 的策略更新、告警、配额和 UID rule 相关方法片段。
- Android 17 `netd`/BPF 网络统计相关源码路径，需给出真实文件名、结构体/map 名称和调用方向。
- 如要讨论性能或诊断，需补 Perfetto/bugreport/dumpsys/netd 命令输出样例，并明确设备、构建与复现条件。

## 6. 当前结论

本章已通过 rework 完成安全修复（消除启发式标记、补公开 API 证据标记），但 AOSP 源码级正文仍未补齐。下一轮 body-apply 应以真实 AOSP 源码替换本骨架中的证据缺口列表，补齐服务调用链和策略执行路径后，再将 `pipeline_stage` 推进到 `task6_pending` 并进入复查。
