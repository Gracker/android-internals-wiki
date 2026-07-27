---
title: "Android 17 NFC 性能优化与无接触支付"
chapter: "18.2"
status: needs-review
applicable_versions: "Android 16 (API 35) - Android 17 (API 37)"
tags: ["Android", "连接性", "NFC"]
related_chapters: ["ch05-cpu-power"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-07"
gap_source: "daily-info"
last_verified: "2026-07-27"
last_verified_against: "rework source-boundary check; routed material is unrelated audio hardening research, only Android Developers NFC docs retained as background"
confidence: low
pipeline_stage: needs-rework
task6_state: needs-source-material
task9_state: rework-returned-source-boundary
last_deep_review_at: "2026-07-27T12:35:27+08:00"
last_deep_review_run_id: "20260727-123527-deep-review-455b9e9f"
last_rework_at: "2026-07-27T17:35:55+08:00"
last_rework_run_id: "20260727-173511-rework-455b9e9f"
rework_summary: "Rework 未发现可支撑 NFC 支付性能结论的一手材料；已统一状态边界、强化不可发布说明，并保留为待补 NFC/AOSP 证据的 needs-review 页面。"
sources:
  - type: official-docs
    ref: "Android Developers: NFC basics / advanced NFC"
    url: "https://developer.android.com/develop/connectivity/nfc"
    status: background-reference-only
  - type: routed-material
    ref: "DeepResearch/2026-07-05-background-audio-hardening-power.md"
    status: rejected-unrelated-to-nfc-payment
---

# Android 17 NFC 性能优化与无接触支付

## Rework 结论

本轮 rework 没有把本章推进为 `ready-for-review`。预运行只提供了一份“后台音频硬化与播放功耗治理”材料，其主题和证据链集中在 `AudioService`、`HardeningEnforcer`、`AudioFlinger`、AppOps 音频控制、蓝牙音频豁免与后台播放功耗治理；材料中没有 NFC、HCE、`NfcService`、Secure Element、Reader Mode 调度、支付 APDU 路径、POS 交互时延或无接触支付成功率证据。因此该材料继续被隔离为 `rejected-unrelated-to-nfc-payment`，不能用于恢复 NFC 支付性能正文。

当前文件保留为安全的回流页，而不是正式技术结论页：它只说明哪些范围可以继续研究、哪些断言已经被删除、下一轮需要补齐哪些证据。由于缺少 NFC 相关一手材料，`pipeline_stage` 仍保持 `needs-rework`，`task6_state` 标为 `needs-source-material`，`task9_state` 标为 `rework-returned-source-boundary`。

## 为什么不能发布为 Android 17 NFC 性能结论

无接触支付章节必须同时满足三类边界：

1. **平台边界**：只能描述 Android 17 / `android-17.0.0_r1` 中可验证的 NFC framework、系统应用或相关配置变化；不能把厂商钱包、支付网络或终端侧策略泛化为 Android 平台能力。
2. **API 边界**：公开 API、系统 API、隐藏 API 与示例代码必须分开。若没有 Android SDK / AOSP 符号证据，不能写成“Android 17 新增 API”。
3. **性能边界**：支付唤醒时间、APDU 处理延迟、POS 响应时间、成功率、离线交易时长等数字必须有可追溯 benchmark、AOSP 测试、官方文档或厂商白皮书。没有来源时只能列为待验证问题，不能作为结论。

本轮材料不覆盖以上任一 NFC 证据链，因此不能据此推出 Android 17 针对支付链路做了确定性性能优化。

## 当前可安全保留的研究范围

后续如果重新扩写，本章可以围绕以下低风险范围展开，但每一项都需要补充对应来源：

- **公开 NFC 开发模型**：Reader Mode、前台调度、NDEF tag 处理、HCE、`HostApduService` 与常规 tag 读取路径。Android Developers NFC 文档只能作为背景参考，不能单独支撑 Android 17 差异结论。
- **AOSP 源码差异**：围绕 `android-17.0.0_r1` 检查 `packages/apps/Nfc/`、`frameworks/base/core/java/android/nfc/`、`frameworks/base/core/java/android/nfc/cardemulation/` 等路径，并和 Android 16 基线对比真实类、方法、配置或测试变化。
- **支付责任边界**：HCE、Secure Element、wallet 应用、支付网络 tokenization、终端/POS 行为应分层描述。除非有平台源码或官方 API 证明，不能把应用层支付策略写成系统服务能力。
- **性能观测方法**：如果后续讨论延迟，需要说明观测点来自 reader discovery、APDU dispatch、service binding、应用进程唤醒、binder 调用、日志事件或外部终端测量中的哪一层，避免把端到端体验数字误写为 Android 平台保证。

## 已删除且不得恢复的高风险断言

在没有新证据前，下列断言不得恢复到正文：

- `NfcAdapter.enableReaderMode()` 新增 `PRIORITY_HIGH` 参数。
- Android 17 将支付应用唤醒时间优化到 120ms 以内，或将支付响应时间优化到 80ms。
- `PaymentManager.setDynamicSecurityLevel()`、`PaymentManager.enableOfflinePayment()`、`CrossDevicePaymentManager` 等未验证 API。
- 系统根据车辆传感器自动启停 NFC 支付、支持语音支付确认、离线交易缓存 72 小时、多设备账单分摊等产品化能力。
- 零售、公交、售货机场景的成功率、并发量、取货时间缩短等量化收益。
- 从“后台音频硬化”材料外推 NFC 支付调度、功耗或支付安全结论。

## 下一轮补证清单

1. **AOSP 差异证据**：对比 Android 16 与 `android-17.0.0_r1` 的 NFC 相关目录，列出可复核 commit、类、方法、flag、配置或测试变化。
2. **公开 API 证据**：确认 Android 17 是否新增 NFC / HCE / card emulation API、常量或行为说明；若没有新增项，应明确写成“无公开新增 API 证据”。
3. **性能数据来源**：任何 ms、百分比、成功率或功耗数字必须绑定来源；没有来源时只能写成观测建议。
4. **支付安全边界**：分别处理 HCE、Secure Element、HostApduService、钱包应用和支付网络职责，避免平台/应用/网络混写。
5. **章节归并判断**：如果后续仍无法取得 NFC 一手材料，应考虑由目录治理决定是否保留占位、合并到连接性综述，或删除该 niche 章节；本 rework lane 不新增章节，也不改 `src/SUMMARY.md`。

---

## 参考资料

1. [背景参考: Android Developers NFC 文档, developer.android.com/develop/connectivity/nfc]
2. [不采纳: DeepResearch/2026-07-05-background-audio-hardening-power.md —— 音频硬化材料，与 NFC 支付主题不匹配]
3. [待补: AOSP android-17.0.0_r1, packages/apps/Nfc/]
4. [待补: AOSP android-17.0.0_r1, frameworks/base/core/java/android/nfc/]
