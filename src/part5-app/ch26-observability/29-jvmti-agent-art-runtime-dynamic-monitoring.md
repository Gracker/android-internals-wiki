---
title: "26.29 JVMTI Agent — ART 运行时动态监控的实验入口与证据边界"
chapter: "26.29"
status: ready-for-review
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [JVMTI, ART, runtime-monitoring, dynamic-instrumentation, profilo, method-tracing]
related_chapters: ["26.21", "26.23", "26.27", "1.35", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings参考书+AOSP源码+章节深挖"
last_verified: "2026-07-27"
confidence: low
sources:
  - "技术文章/source/juejin-android/2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md"
  - "本章既有提纲: JVMTI/ART/runtime-monitoring"
last_body_apply_at: "2026-07-24T07:15:55+08:00"
last_body_apply_run_id: "20260724-071534-2a71a09c"
last_body_apply_source: "source-index:91"
task2b_state: fixed
task6_state: needs-rework
task9_state: needs-rework
pipeline_stage: needs-rework
reviewed_date: "2026-07-27"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-27T18:05:34+08:00"
last_review_finalize_run_id: "20260727-180515-f7d5f885"
last_rework_at: "2026-07-25T13:35:15+08:00"
last_rework_run_id: "20260725-133515-rework-afd64006"
rework_summary: "2026-07-27 复核判定仍需 rework：当前唯一正文材料是 Android CLI 预览版介绍，只能支撑实验工程/SDK/设备/UI/文档检索入口；无法支撑题名中的 JVMTI Agent、ART runtime/jvmti、attachAgent、事件回调、对象 tag 或线上 attach/detach 源码结论。需补 Android 17.0.0_r1 ART/Framework 一手源码与可复现实测后再 finalized。"
---

# 26.29 JVMTI Agent — ART 运行时动态监控的实验入口与证据边界

## 本节定位

JVMTI Agent 的研究目标，是把 ART 运行期的部分行为转化为可观察、可复核的调试或监控证据；但当前可用材料主要证明的是 **Android CLI 可帮助 Agent/CI 稳定完成 Android 工程、SDK、设备、截图和官方知识检索流程**，并不能直接证明 Android 17.0.0_r1 中 `android.os.Debug.attachAgent`、`Agent_OnLoad` / `Agent_OnUnload`、MethodEntry/MethodExit、FieldAccess/FieldModification、TagObject/GetObjectsWithTags 或线上 attach/detach 的源码语义。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md][来源: 本章既有提纲]

因此，本节把原先过宽的“运行时动态监控结论”收敛为一个安全口径：**Android CLI 是 JVMTI/ART 实验的环境与证据入口，不是 JVMTI 运行时机制本身的证明来源**。后续若要扩展为完整 JVMTI Agent 章节，仍必须基于 Android 17.0.0_r1 / android17-6.18 对 ART `runtime/jvmti` 与 Framework attach API 做逐项源码复核和实测闭环。[来源: 本章既有提纲]

## Android CLI 能安全支撑什么

材料把 Android CLI 描述为 Android 团队发布的预览版命令行入口，强调它面向 Agent 工作流，提供项目模板、SDK 管理、设备/界面操作、文档检索和 skills 安装等能力；这些能力适合放在 JVMTI 排障链路的“准备与取证”层。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

在本章范围内，它可以安全承担三类工作：

1. **显式化实验工程**：材料给出 `android create list`、`android create --dry-run --verbose empty-activity-agp-9` 和 `android create -o ./DemoApp empty-activity-agp-9`。这些命令适合记录样例工程从 dry-run 到落盘的过程，避免 Agent 临时拼 Gradle、目录和模板。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]
2. **显式化 SDK 与设备前置条件**：材料说明 `android sdk install` 可指定包名、版本或渠道，并给出 `android sdk install platforms/android-34 build-tools/34.0.0` 与 `android sdk list 'platforms/.*'` 示例。它们适合记录实验需要的 SDK 包和已安装平台，降低“装错版本、路径混乱、隐式依赖”的复现风险。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]
3. **显式化 UI 触发与外部证据**：材料列出 `android screen capture --annotate`、`android screen resolve --screenshot=ui.png --string="input tap #5"` 和 `android layout --diff`。这些命令适合把方法追踪或字段观察实验中的外部触发动作、截图和布局变化留作验收证据。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

## Agent 工作流中的使用边界

材料提到 `android init` 会安装 `android-cli` skill，帮助 Agent 理解并使用 Android CLI；还提到 `android skills list --long`、`android skills find 'performance'`、`android skills add --agent='gemini' edge-to-edge` 这类命令可管理 Markdown 形式的工作流指令集。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

接入 JVMTI 研究时，需要保留两条边界：

- **skills 约束操作，不替代源码核验**：`android docs search` / `android docs fetch` 可以作为官方知识检索入口，帮助定位推荐做法或文档主题；但 ART JVMTI capability 子集、attach 生命周期、事件语义、对象 tag 行为和卸载清理仍要以 Android 17.0.0_r1 源码与可复现实验为准。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md][来源: 本章既有提纲]
- **预览版工具不扩大版本边界**：材料把 Android CLI 标为“预览版”，示例中出现 `platforms/android-34`，不能据此推出 Android 18/API 38 及之后的运行时结论。AIW 当前主线仍限定在 Android 17.0.0_r1 / API 37 及 android17-6.18 内核基线。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

## 建议的 JVMTI 实验记录模板

当用 Agent 协助验证 JVMTI Agent 或 ART 运行时监控时，建议至少保留下面四层证据。这样即便正文暂不写入 `attachAgent`、事件回调或对象 tag 的结论，也能为后续源码复核和实测补章留下可复现入口。

| 证据层 | 建议记录项 | 作用 |
| --- | --- | --- |
| 工程生成 | `android create --dry-run --verbose ...` 与实际 `android create -o ...` 输出 | 证明样例工程如何生成，便于回看模板、Gradle 配置和初始文件差异。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| SDK 环境 | `android sdk install ...` 与 `android sdk list 'platforms/.*'` 输出 | 证明实验所需平台和 build-tools，不把环境问题误判为 JVMTI 行为差异。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| 设备/UI 触发 | `android screen capture --annotate`、`android screen resolve ...`、`android layout --diff` 输出 | 证明触发路径和界面状态，方便把外部操作与运行时观测时间线对齐。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| 知识检索 | `android docs search ...` 与 `android docs fetch ...` 输出 | 作为官方文档导航线索；最终运行时结论仍需源码和实测确认。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |

## 与三类动态监控方案的选型关系

本章既有提纲把 JVMTI、字节码插桩和 XTrace 放在同一组选型问题里：字节码插桩偏编译期，XTrace 偏 ART hook，JVMTI 偏运行时 Agent。[来源: 本章既有提纲]

在当前证据水平下，只能得出一个工作流层面的结论：如果目标是快速生成样例、安装指定 SDK、启动设备、部署运行、截图定位和查官方文档，Android CLI 可以降低 Agent/CI 的流程摩擦；如果目标是证明方法进入/退出事件、字段访问/修改事件、对象标记、agent 加载卸载或线上动态挂载策略，则仍需另起源码核验与实测记录，不能直接从 Android CLI 材料推导。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md][来源: 本章既有提纲]

## 后续源码复核清单

以下条目保留为后续复查清单，不在本节中当作已验证结论：

- `android.os.Debug.attachAgent` 在 Framework/API 层的入口、权限和错误处理边界。[来源: 本章既有提纲]
- `Agent_OnLoad` / `Agent_OnUnload` 在 ART 加载与清理链路中的调用条件。[来源: 本章既有提纲]
- MethodEntry/MethodExit 与 FieldAccess/FieldModification 事件在 Android 17.0.0_r1 上的 capability 条件、开启成本和采样策略。[来源: 本章既有提纲]
- TagObject/GetObjectsWithTags 这类对象标记能力在泄漏检测或堆对象归因中的可用边界。[来源: 本章既有提纲]
- 线上 attach/detach 是否可用、可控和可回滚，需要结合目标构建类型、签名、调试属性、SELinux/权限与应用发布策略单独验证。[来源: 本章既有提纲]

## 复查结论

本轮 finalize 复核结论更新为“保留 `ready-for-review`、但 `task6_state` / `task9_state` / `pipeline_stage` 标记 `needs-rework`”。原因不是正文仍包含已确认为真的错误结论，而是章节题名与目标范围仍指向 JVMTI Agent / ART runtime dynamic monitoring；当前唯一可追溯正文材料却只是 Android CLI 预览版介绍，只能支撑实验环境、SDK、设备/UI 操作和文档检索入口，不能支撑 `runtime/jvmti`、`android.os.Debug.attachAgent`、Agent 加载卸载、事件回调、对象 tag 或线上 attach/detach 的 Android 17.0.0_r1 源码级结论。

在补齐 Android 17.0.0_r1 ART/Framework 一手源码与可复现实测前，本章可以作为“JVMTI 实验准备与证据边界”草稿保留，但不应进入 finalized，也不应被引用为 JVMTI API/ART 语义的最终章节。

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 53.md]
