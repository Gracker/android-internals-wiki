---
title: "26.29 JVMTI Agent — ART 运行时动态监控接口与线上方法追踪"
chapter: "26.29"
status: ready-for-review
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [JVMTI, ART, runtime-monitoring, dynamic-instrumentation, profilo, method-tracing]
related_chapters: ["26.21", "26.23", "26.27", "1.35", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings参考书+AOSP源码+章节深挖"
last_verified: "2026-07-24"
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
reviewed_date: "2026-07-24"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-24T08:05:55+08:00"
last_review_finalize_run_id: "20260724-080541-db5bc0cd"
rework_reason: "当前正文主要是 Android CLI 工作流补记和既有提纲，尚未完成 Android 17.0.0_r1 ART/JVMTI 源码级核验；不能 finalize。"
---

# 26.29 JVMTI Agent — ART 运行时动态监控接口与线上方法追踪

<!-- outline-start -->
## 要点

### 🔹 JVMTI 是什么：JVM Tool Interface 的 Android 之旅
{JVMTI 定义、标准 JVM 工具接口规范、ART 如何实现 JVMTI 子集、与 Desktop JVM 的差异}

### 🔹 ART JVMTI 实现架构与能力边界
{art/runtime/jvmti 目录结构、agent 加载机制、支持的 capability 子集、与 OpenJDK JVMTI 的差异}

### 🔹 Agent 加载与卸载：JVMTI Agent_OnLoad / Agent_OnUnload 生命周期
{android.os.Debug.attachAgent、JVMTI 启动模式、attach 时机、卸载清理}

### 🔹 方法级性能监控：MethodEntry / MethodExit 事件
{如何注册方法进/出事件、采样 vs 全量、性能开销实测、与 Trace.beginSection 的对比}

### 🔹 字段访问监控：FieldAccess / FieldModification 事件
{监控对象字段读写、内存泄漏检测场景、 WatchpointDescription 用法}

### 🔹线上动态挂载与卸载策略
{生产环境安全 attach/detach、白名单控制、权限校验、与 ProGuard/R8 混淆的配合}

### 🔹 JVMTI vs 字节码插桩 vs XTrace：三大动态监控方案选型
{26.21 字节码插桩（编译期）vs 26.23 XTrace（ART hook）vs JVMTI（运行时 agent）的成本/精度/覆盖面对比}

## 扩展

### 🔸 Facebook Profilo 的 JVMTI 集成路径
{Profilo 如何在 Android 上使用 JVMTI、与 ATrace 收集的配合}

### 🔸 JVMTI 在内存泄漏检测中的高级用法
{TagObject / GetObjectsWithTags、堆快照增量标记}

### 🔸 JVMTI 性能开销量化与采样策略优化
{不同 capability 组合的 CPU 开销、内存开销、对帧率的影响}

<!-- outline-end -->

## 本节定位

> **审阅状态（2026-07-24）**：本章暂不 finalize。当前正文只安全说明 Android CLI 可作为 JVMTI 实验环境与证据采集入口，并明确它不能替代 ART/JVMTI 源码结论；但章节标题承诺的 `android.os.Debug.attachAgent`、`Agent_OnLoad` / `Agent_OnUnload`、MethodEntry/MethodExit、FieldAccess/FieldModification、对象 tag 与线上 attach/detach 边界仍停留在提纲与待核验清单阶段。后续需要基于 Android 17.0.0_r1 / android17-6.18 对 ART `runtime/jvmti` 与 Framework attach API 做逐项源码复核后，才能恢复 `ready-for-review` 或推进 `finalized`。

JVMTI Agent 的价值在于把“线上运行时正在发生什么”变成可观察事件，而不是把监控逻辑提前写死在业务代码或编译期插桩里；本章先保留既有提纲中的 JVMTI、ART、`android.os.Debug.attachAgent`、方法事件、字段事件、线上 attach/detach、Profilo、对象标记与采样策略这些研究轴线，后续源码复核仍以 Android 8.0（API 26）到 Android 17（API 37）为边界。[来源: 本章既有提纲]

本次补入的 Android CLI 材料不直接证明 JVMTI API 细节，而是补齐“如何在 Agent/CI 工作流中稳定搭建实验环境、运行样例、抓取界面证据、检索官方知识”的操作层：材料明确把 Android CLI 描述为 Android 团队发布的预览版命令行入口，可在终端完成 Android 开发关键闭环，并强调它面向 Agent 工作流，配套 Android skills 与 Android Knowledge Base。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

## 与 JVMTI 排障链路的关系

在 JVMTI 章节中，Android CLI 更适合放在“实验入口”和“证据采集”层，而不是放在“运行时注入机制”层。材料给出的核心动机是把环境、模板、设备、部署、知识与技能标准化，从而减少自动化或 Agent 流程在 SDK 组件、路径、项目创建、设备启动、安装运行、截图定位与查文档上的摸索成本。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

因此，一个安全的 JVMTI 排障闭环可以拆成三段：

1. **环境与样例准备**：使用 `android create list` 查看模板，使用 `android create --dry-run --verbose empty-activity-agp-9` 先模拟生成结果，再用 `android create -o ./DemoApp empty-activity-agp-9` 落盘样例工程；这些命令来自材料的“创建项目：先 dry-run 再落盘”部分。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]
2. **SDK 与设备准备**：材料指出 Android CLI 提供 `android sdk install`，可指定包名、版本或渠道，并给出 `android sdk install platforms/android-34 build-tools/34.0.0` 与 `android sdk list 'platforms/.*'` 这类命令示例；在本章语境下，它们可用于把 JVMTI 实验工程和目标设备环境显式化，避免 Agent 隐式猜 SDK 版本。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]
3. **运行与 UI 证据采集**：材料列出 `android screen capture --annotate` 可给 UI 元素打标签框，`android screen resolve --screenshot=ui.png --string="input tap #5"` 可把标签解析成真实坐标，并提到 `android layout --diff` 可导出布局树变化；这些能力可以作为 JVMTI 方法追踪或字段监控实验的外部触发与验收证据。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

## Agent 工作流中的边界

材料强调 `android init` 会安装 `android-cli` skill，帮助 Agent 理解并使用 Android CLI；材料还说明 `android skills` 可以查找或安装 Markdown 形式的工作流指令集，示例命令包含 `android skills list --long`、`android skills find 'performance'` 与 `android skills add --agent='gemini' edge-to-edge`。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

把这组能力接入 JVMTI 研究时，需要明确两条边界：

- **CLI/skill 只约束工程动作，不替代源码结论**：材料说 `android docs search` 与 `android docs fetch` 可通过 Knowledge Base 校准到最新推荐模式；在本章中，这类命令适合用于检索官方建议、补全实验步骤，但不能替代对 ART JVMTI 实现、capability 子集、attach 生命周期与事件语义的源码级核验。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md][来源: 本章既有提纲]
- **预览版工具不扩大 Android 版本边界**：材料称 Android CLI 为“预览版”，并用 `platforms/android-34` 作为 SDK 安装示例；AIW 当前基线仍固定在 Android 17.0.0_r1 / API 37，因此本章只把这些命令视为工作流样例，不由此推出 Android 18/API 38 及之后的运行时结论。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

## 建议的实验记录模板

当用 Agent 协助验证 JVMTI Agent 时，建议把每次实验记录成下面四类证据，避免“工具跑过”但无法复现：

| 证据层 | 记录项 | 为什么与本章相关 |
| --- | --- | --- |
| 工程生成 | `android create --dry-run --verbose ...` 与实际 `android create -o ...` 输出 | 材料强调先 dry-run 再落盘，适合保留工程初始状态与生成差异。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| SDK 环境 | `android sdk install ...` 与 `android sdk list 'platforms/.*'` 输出 | 材料强调按需安装 SDK 组件，适合记录 JVMTI 样例运行所需平台和 build-tools。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| 设备/UI 触发 | `android screen capture --annotate`、`android screen resolve ...`、`android layout --diff` 输出 | 材料把这些命令定位为 UI 自动化与可视化定位能力，适合为方法进入/退出追踪提供外部触发证据。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| 知识检索 | `android docs search ...` 与 `android docs fetch ...` 输出 | 材料说明 Knowledge Base 可让回答带上最新官方依据；本章后续源码复核可把检索结果作为导航线索，而不是最终判据。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |

## 与三类动态监控方案的初步选型口径

本章既有提纲把 JVMTI、字节码插桩与 XTrace 放在同一组选型问题里：字节码插桩偏编译期，XTrace 偏 ART hook，JVMTI 偏运行时 Agent。[来源: 本章既有提纲]

Android CLI 材料给出的补充视角是“让 Agent/CI 能稳定执行 Android 工程动作”：如果目标是快速生成样例、安装指定 SDK、启动设备、部署运行、截图定位和查官方文档，CLI 可以降低工作流摩擦；如果目标是证明方法事件、字段事件、对象标记或 attach/detach 的运行时语义，仍需回到 JVMTI/ART 章节主线做源码与实测闭环。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md][来源: 本章既有提纲]

## 后续复查清单

- 对 `android.os.Debug.attachAgent`、`Agent_OnLoad`、`Agent_OnUnload`、MethodEntry/MethodExit、FieldAccess/FieldModification、TagObject/GetObjectsWithTags 等条目逐项做 Android 17.0.0_r1 源码核验。[来源: 本章既有提纲]
- 在实验章节中保留 Android CLI 的命令输出、SDK 列表、设备截图标注、layout diff 和 docs fetch 结果，作为 Agent 协助复现的证据链。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]
- 不把 Android CLI 的预览版定位、token 节省比例或任务速度提升数值推广为 JVMTI 性能结论；材料中的 70%+ token 使用量下降和 3 倍左右速度提升只属于官方内部实验对 Android CLI/Agent 工作流的描述。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 53.md]
