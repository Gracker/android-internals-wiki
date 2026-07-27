---
title: "Android 17 NetworkStatsService 与 NetworkPolicyManagerService 移动数据 quota 限速源码路径"
chapter: "24.20"
status: "draft"
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [network, io, http]
last_draft_polish_at: "2026-07-27T23:38:48+08:00"
last_draft_polish_run_id: "20260727-233848-draft-polish-43dea43a"
task6_state: "blocked-source-material-required"
task9_state: "pending"
pipeline_stage: "draft_needs_body_apply"
last_verified: "2026-07-27"
last_verified_against: "Android baseline android-17.0.0_r1; consecutive draft-polish runs (2026-07-26, 2026-07-27) with empty materials; no routed source slices"
confidence: low
sources:
  - type: source-material-required
    note: "Pre-run materials array was empty for consecutive runs (2026-07-26, 2026-07-27); body is intentionally constrained to review scaffolding and source requests until AOSP/official material is routed."
---

# Android 17 NetworkStatsService 与 NetworkPolicyManagerService 移动数据 quota 限速源码路径

> **Draft-polish 结论（2026-07-27，连续第二轮）**：本轮继续没有路由到 AOSP 源码切片、官方文档、设备 trace、代码搜索结果或前序 body-apply 材料。这是连续第二个 draft-polish 周期（2026-07-26、2026-07-27）出现空 `materials`，因此本章仍保持 `draft`，不做无来源扩写。章节骨架（版本边界、待验证问题、原稿风险记录、补材料清单、临时读者指引）已在 2026-07-26 收敛完成，本轮仅刷新 run 元数据并再次确认阻塞原因。原稿的未验证伪代码、类名与 API 断言仍不能在 `android-17.0.0_r1` 基线上作为已验证源码结论保留。等待 body-apply/source-material 路由真实 AOSP/官方材料后，再进入 `ready-for-review`。

## 1. 版本与范围边界

- Android 平台基线：`android-17.0.0_r1` / Android 17。
- 主题范围：`NetworkStatsService`、`NetworkPolicyManagerService`、`netd` 与内核/BPF 统计路径中，和移动数据用量统计、配额告警、策略执行相关的源码链路。
- 当前状态：**待补源码材料**。本章暂不声称 Android 17 新增了特定 quota 限速 API、特定 BPF map 数量、特定防火墙链名称或应用可直接调用的隐藏接口。
- 不纳入范围：Android 18/API 38+ mainline 变化、未路由的第三方 SDK 策略、运营商计费后台实现。

## 2. 已收敛的待验证问题

后续 body-apply 应优先用 `android-17.0.0_r1` 源码回答下列问题，并在正文中逐条标注文件路径、类/方法名和验证时间：

1. `NetworkStatsService` 在 Android 17 中如何从内核或 `netd` 侧读取 UID/iface/template 维度的统计数据？
2. `NetworkPolicyManagerService` 如何维护 `NetworkPolicy`、告警阈值、配额规则和受限网络策略？
3. 移动数据 quota 超限后，系统实际执行的是阻断、后台限制、告警通知、metered 策略更新，还是其他策略组合？
4. `netd`/BPF/iptables 或 nftables 路径在 Android 17 中各自承担哪些职责？哪些名称、map、chain 或命令是源码中真实存在的？
5. 应用开发者能够通过公开 API 观测哪些信号，例如 `NetworkStatsManager`、`ConnectivityManager`、`JobScheduler`、`WorkManager` 约束或 Data Saver 相关回调？哪些接口属于 system/hidden API，不能作为普通应用指南？

## 3. 原稿风险与处理

本轮移除了原稿中的大段未验证示例代码和实现断言，包括但不限于：

- 未证实的 `NetworkQuotaManager`、`NetworkQuotaEnforcer`、`QuotaExceededHandler`、`AlertObserver` 派生类示例。
- 未证实的 `netd.setNetworkQuota(...)`、`addNetworkQuotaRule(...)`、`addFirewallRule(...)` 调用链。
- 未证实的 “FastDataInput 包含 4 个 BpfMap”、`uid_rx_bytes`/`uid_tx_bytes` 等 map 名称、XDP quota monitor 示例。
- 未证实的 80%/90%/100% 分级限速策略、50% 带宽限速、防火墙链 `quota_*` 示例。
- 未证实的应用层配额扩展、配额监控、测试工具与性能指标样例。

这些内容可能来自占位稿或生成稿，缺少可追溯源码证据。为避免把未验证代码当成 Android 17 平台事实，本章暂不推进到 `ready-for-review`。

## 4. 后续补材料清单

进入下一轮正文修复前，至少需要补齐以下材料之一组：

- AOSP `android-17.0.0_r1` 中 `frameworks/base/services/core/java/com/android/server/net/NetworkStatsService.java` 的相关方法片段。
- AOSP `android-17.0.0_r1` 中 `frameworks/base/services/core/java/com/android/server/net/NetworkPolicyManagerService.java` 的策略更新、告警、配额和 UID rule 相关方法片段。
- Android 17 `netd`/BPF 网络统计相关源码路径，需给出真实文件名、结构体/map 名称和调用方向。
- Android 公开文档或 SDK API 参考中与 `NetworkStatsManager`、Data Saver、metered network、后台网络约束相关的开发者可用边界。
- 如要讨论性能或诊断，需补 Perfetto/bugreport/dumpsys/netd 命令输出样例，并明确设备、构建与复现条件。

## 5. 临时读者指引

在材料补齐前，本章只能作为选题占位与复查清单使用。读者若需要实现应用侧移动数据友好策略，应优先采用公开且稳定的系统信号：

- 识别 metered network 后减少大文件下载、预取和自动播放。
- 对后台任务使用网络约束，避免在受限网络或 Data Saver 场景下强行同步。
- 用 `NetworkStatsManager` 等公开 API 做合规的历史用量观察，但不要依赖隐藏服务或假定系统内部 quota 阈值。
- 对用户可见的大流量行为提供 Wi‑Fi only、漫游禁用、低码率/低清晰度等产品开关。

## 6. 当前结论

本章尚未完成源码级验证。下一轮应以真实 AOSP/官方文档材料替换本骨架，补齐服务调用链、策略边界和应用可用 API 后，再将 `pipeline_stage` 推进到 `task6_pending` 并进入人工/自动复查。
