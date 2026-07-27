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
last_verified_against: "source-boundary audit only; no NFC AOSP evidence routed in this run"
confidence: low
pipeline_stage: needs-rework
task6_state: needs-rework
task9_state: deep-review-returned
last_deep_review_at: "2026-07-27T12:35:27+08:00"
last_deep_review_run_id: "20260727-123527-deep-review-455b9e9f"
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

## Deep-review 结论

本轮 deep-review 没有把原稿推进为可发布正文。预运行只路由到一份“后台音频硬化与播放功耗治理”材料，内容聚焦 `AudioService`、`HardeningEnforcer`、`AudioFlinger` 与蓝牙音频豁免，不包含 NFC、HCE、支付路径、`NfcService`、Secure Element 或无接触支付延迟证据。因此该材料不能支撑本章原有的 NFC 支付性能结论。

为避免把未证实内容继续留在 AIW 正文中，本次已删除原稿中缺少来源支撑的 Android 17 NFC 支付新 API、延迟数字、动态安全策略、离线支付、跨设备支付协同和车载支付自动化等断言，并将章节回流为 `needs-review` / `needs-rework`。

## 当前可保留的范围

本章后续可以继续研究 Android 16 到 Android 17 范围内的 NFC 与无接触支付体验，但必须先补齐 NFC 相关一手材料。安全可研究的边界包括：

- Android NFC 公开开发模型：Reader Mode、前台调度、NDEF、HCE 与常规 tag 读取路径。
- AOSP `android-17.0.0_r1` 中 NFC 应用与 framework 代码的真实变化：例如 `packages/apps/Nfc/`、`frameworks/base/core/java/android/nfc/`、`frameworks/base/core/java/android/nfc/cardemulation/` 等路径。
- 支付场景只能在有源码、官方文档或支付网络公开规范支撑时讨论；不能从“Android 17 优化”泛化推出具体支付成功率、POS 响应时延或硬件厂商自适应能力。

## 回流待补材料

下一轮 body-apply / source-review 需要补齐以下证据后再扩写：

1. **AOSP 差异证据**：对比 Android 16 与 `android-17.0.0_r1` NFC 相关目录，列出真实 commit、类、方法或配置变化。
2. **公开 API 证据**：确认是否存在新增 NFC API、flag 或常量；若不存在，不得保留“新增参数”类表述。
3. **性能数据来源**：任何“80ms、120ms、99.9%”等数字必须来自可追溯 benchmark、AOSP 测试、厂商白皮书或官方文档。
4. **支付安全边界**：HCE、Secure Element、HostApduService 与支付网络责任边界需要分开描述，避免把应用层支付策略写成 Android 平台 API。

## 本轮删除的高风险断言

- `NfcAdapter.enableReaderMode()` 新增 `PRIORITY_HIGH` 参数。
- Android 17 将支付应用唤醒时间优化到 120ms 以内、支付响应时间优化到 80ms。
- `PaymentManager.setDynamicSecurityLevel()`、`PaymentManager.enableOfflinePayment()`、`CrossDevicePaymentManager` 等未验证 API。
- 系统根据车辆传感器自动启停 NFC 支付、支持语音支付确认、离线交易缓存 72 小时、多设备账单分摊等产品化能力。
- 零售/公交/售货机场景的成功率、并发量、取货时间缩短等量化指标。

---

## 参考资料

1. [背景参考: Android Developers NFC 文档, developer.android.com/develop/connectivity/nfc]
2. [不采纳: DeepResearch/2026-07-05-background-audio-hardening-power.md —— 音频硬化材料，与 NFC 支付主题不匹配]
3. [待补: AOSP android-17.0.0_r1, packages/apps/Nfc/]
4. [待补: AOSP android-17.0.0_r1, frameworks/base/core/java/android/nfc/]
