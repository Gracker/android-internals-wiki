---
title: "内容验证标准说明"
chapter: "preface.4"
status: ready-for-review
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-08-05"
last_verified_against: "AOSP android-17.0.0_r1; Android Common Kernel android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: official
    path: "https://android.googlesource.com/platform/manifest/+/refs/tags/android-17.0.0_r1/default.xml"
  - type: official
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/"
tags: [introduction, verification, source-code, evidence]
pipeline_stage: reworked
task6_state: ready-for-review
task9_state: reworked
last_rework_at: "2026-08-05T21:35:21+08:00"
last_rework_run_id: "20260805-213521-rework-d44d97f6"
last_rework_log: "logs/rework/2026-08-05-20260805-213521-rework-d44d97f6-rework.md"
---

# 内容验证标准说明

技术结论必须能回到证据。源码机制优先用固定版本的代码验证，公开 API 与兼容要求优先用官方文档验证，运行时行为再用 trace、日志、命令输出或可复现实验补充。单凭二手文章、搜索摘要或没有条件说明的性能数字，不能标为已验证。

这是全书统一采用的验证口径，不替代各技术章节自己的证据链。它只定义“怎样标注、怎样降级、怎样关闭待核对项”，不为某个 framework、kernel 或设备行为作额外机制结论。

## 默认源码基线

全书采用两套互相独立的默认锚点：

- Android 平台：Android 17（API 37），AOSP tag 为 `android-17.0.0_r1`，以该 tag 的 manifest 作为平台项目集合入口。
- Android Common Kernel：6.18，ACK tag 为 `android17-6.18-2026-06_r6`。

平台代码和内核代码不能混用版本名。`android-17.0.0_r1` 用于 `frameworks/base`、`frameworks/native`、`system/core`、ART、Bionic 等 AOSP 项目；`android17-6.18-2026-06_r6` 用于 Android Common Kernel。设备厂商可能在 ACK 之上叠加 SoC 与产品补丁，因此 ACK 源码只能证明公共内核基线，不能替代具体设备的 kernel commit、配置与 vendor 实现。

如果一个章节没有单独声明更窄的版本范围，应按上述两条默认基线阅读。若章节需要引用更早版本、厂商分支、实验构建或主线开发分支，正文必须把它们从 Android 17 确定性结论中分离出来。

## 一条源码锚点应包含什么

正文中的源码依据至少要能回答四个问题：

1. **版本**：代码来自哪个固定 tag。
2. **项目与路径**：例如 `frameworks/base/services/core/java/com/android/server/am/OomAdjuster.java`。
3. **符号**：对应哪个类、方法、结构体、枚举或配置项。
4. **结论边界**：这段代码能证明什么，不能证明什么。

行号可以帮助定位，但不能单独充当锚点。文件变化会让行号漂移，tag、路径与符号组合更适合长期核对。正文引用代码节选时，还要说明省略范围，不能把伪代码写成 AOSP 原文。

一条合格的源码锚点可以写成“`android-17.0.0_r1` / `frameworks/base/.../OomAdjuster.java` / `OomAdjuster#updateOomAdjLocked`，用于说明进程 adj 计算入口；不证明厂商 LMKD 参数”。这种写法比只写“见源码第 N 行”更适合长期维护。

## 版本演进怎样处理

讲版本迭代的章节可以引用 Android 17 以前的 tag，目的是对比旧行为、定位引入版本或解释兼容分支。此类段落需要同时写明旧版本与 Android 17 的观察结果，不能让旧 tag 变成整章的默认依据。

Android 17 是本书确定性结论的最高版本。来自 `main`、`master`、Android 18 或后续版本的代码只能作为未来变化线索，不能反推 Android 17 已经具备相同行为。如果章节必须讨论尚未发布或更高版本，应明确隔离为“超出本书基线”，不写进 Android 17 的结论。

当未来线索与 Android 17 基线冲突时，正文应优先保留 Android 17 结论，并把未来变化放入独立段落或脚注。只有当章节重新验证到新的正式基线并同步更新章节元数据后，才能把新行为提升为正文默认结论。

## 证据等级

- `high`：关键判断由固定 tag 源码直接支持，并有官方文档、测试、trace 或另一条独立源码路径交叉验证。
- `medium`：关键判断由一条可靠的一手来源支持，但缺少运行时或跨模块交叉验证。
- `low`：只有旧版本、二手资料、厂商单机现象或尚未复现的推断。此类内容必须保留限制说明，不能写成通用机制。

置信度描述证据强度，不代表内容完成度。章节元数据中的编辑状态与正文的“已验证”“待核对”“版本边界”等技术结论互不替代。

如果一个章节混合了不同证据强度，应以关键结论的最低可靠环节决定整章 `confidence`，并在正文中标出高风险段落。局部未完成项不能靠把整章设为 `high` 来掩盖；反过来，流水线的 `needs-review` 也不能自动否定已经由固定 tag 支持的技术段落。

## 待核对项怎样关闭

正文中出现“待核对”“待复现”“需要实机确认”等标注时，应视为未关闭的技术风险，而不是编辑备注。关闭这类标注至少需要补齐以下内容之一：

- 固定 tag 源码能够直接证明该机制，并且正文写清版本、路径、符号与边界。
- 官方文档或兼容性要求能够直接证明 API/行为约束，并且章节说明适用 API 级别。
- trace、日志、命令输出或实验记录能够证明运行时现象，并且记录设备、构建、采集工具和复现条件。

如果只能补到二手资料、搜索摘要或未注明条件的性能数字，应保留限制说明并把相关结论降级，不应把标注删除后写成通用事实。

## 来源清单与章节标注

章节元数据中的 `sources` 是入口清单，不等于正文全部证据。每个包含关键机制结论的章节，正文仍应在相关段落附近给出可定位的 tag、路径、符号、文档页或实验记录。只在 YAML 中放一个仓库根路径，不能证明具体结论。

`last_verified_against` 应写明本次验证覆盖的基线，例如 `AOSP android-17.0.0_r1` 与 `Android Common Kernel android17-6.18-2026-06_r6`。如果章节只验证了其中一部分，不应把另一部分写成已覆盖。`last_verified` 记录最近一次证据核对日期，不应仅因文字润色自动更新。

## 实机与性能数据

源码只能说明实现和条件，不能自动证明设备上的耗时、功耗或收益。性能数字必须给出设备、构建类型、版本、负载、采样工具、样本量和对照基线。厂商 ROM、芯片驱动、HAL、内核配置或温控策略会改变结果时，需要明确写出设备边界。

trace 和日志同样要记录采集条件。看到一个 slice 或 counter，只能证明这次采集中出现了对应事件；要把它上升为机制结论，还需要与固定版本源码中的生产位置、参数含义和触发条件对应。

## 标注的使用方式

读到关键判断时，先核对版本，再看路径与符号，最终确认结论是否覆盖当前设备。若正文只给出了待核对标记或证据边界，该段适合作为排查入口，不应直接用于生产决策。源码、运行数据与设备条件能互相对应时，结论才足够稳。
