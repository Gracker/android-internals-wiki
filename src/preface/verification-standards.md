---
title: "内容验证标准说明"
chapter: "preface.4"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1; Android Common Kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: official
    path: "https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/default.xml"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/"
tags: [introduction, verification, source-code, evidence]
---

# 内容验证标准说明

技术结论必须能回到证据。源码机制优先用固定版本的代码验证，公开 API 与兼容要求优先用官方文档验证，运行时行为再用 trace、日志、命令输出或可复现实验补充。单凭二手文章、搜索摘要或没有条件说明的性能数字，不能标为已验证。

## 默认源码基线

全书采用两套互相独立的默认锚点：

- Android 平台：Android 17（API 37），AOSP tag 为 `android-17.0.0_r1`。
- Android Common Kernel：6.18，ACK tag 为 `android17-6.18-2026-06_r6`。

平台代码和内核代码不能混用版本名。`android-17.0.0_r1` 用于 `frameworks/base`、`frameworks/native`、`system/core`、ART、Bionic 等 AOSP 项目；`android17-6.18-2026-06_r6` 用于 Android Common Kernel。设备厂商可能在 ACK 之上叠加 SoC 与产品补丁，因此 ACK 源码只能证明公共内核基线，不能替代具体设备的 kernel commit、配置与 vendor 实现。

## 一条源码锚点应包含什么

正文中的源码依据至少要能回答四个问题：

1. **版本**：代码来自哪个固定 tag。
2. **项目与路径**：例如 `frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java`。
3. **符号**：对应哪个类、方法、结构体、枚举或配置项。
4. **结论边界**：这段代码能证明什么，不能证明什么。

行号可以帮助定位，但不能单独充当锚点。文件变化会让行号漂移，tag、路径与符号组合更适合长期核对。正文引用代码节选时，还要说明省略范围，不能把伪代码写成 AOSP 原文。

## 版本演进怎样处理

讲版本迭代的章节可以引用 Android 17 以前的 tag，目的是对比旧行为、定位引入版本或解释兼容分支。此类段落需要同时写明旧版本与 Android 17 的观察结果，不能让旧 tag 变成整章的默认依据。

Android 17 是本书确定性结论的最高版本。来自 `main`、`master`、Android 18 或后续版本的代码只能作为未来变化线索，不能反推 Android 17 已经具备相同行为。如果章节必须讨论尚未发布或更高版本，应明确隔离为“超出本书基线”，不写进 Android 17 的结论。

## 证据等级

- `high`：关键判断由固定 tag 源码直接支持，并有官方文档、测试、trace 或另一条独立源码路径交叉验证。
- `medium`：关键判断由一条可靠的一手来源支持，但缺少运行时或跨模块交叉验证。
- `low`：只有旧版本、二手资料、厂商单机现象或尚未复现的推断。此类内容必须保留限制说明，不能写成通用机制。

置信度描述证据强度，不代表文章是否写完。章节的 `status`、`pipeline_stage` 等 frontmatter 字段属于编辑流水线；正文中的“已验证”“待验证”“版本边界”属于技术结论。两者不能互相代替。

## 实机与性能数据

源码只能说明实现和条件，不能自动证明设备上的耗时、功耗或收益。性能数字必须给出设备、构建类型、版本、负载、采样工具、样本量和对照基线。厂商 ROM、芯片驱动、HAL、内核配置或温控策略会改变结果时，需要明确写出设备边界。

trace 和日志同样要记录采集条件。看到一个 slice 或 counter，只能证明这次采集中出现了对应事件；要把它上升为机制结论，还需要与固定版本源码中的生产位置、参数含义和触发条件对应。

## 阅读这些标注

读到关键判断时，先核对版本，再看路径与符号，最终确认结论是否覆盖当前设备。若正文只给出了待验证标记或证据边界，该段适合作为排查入口，不应直接用于生产决策。源码、运行数据与设备条件能互相对应时，结论才足够稳。
