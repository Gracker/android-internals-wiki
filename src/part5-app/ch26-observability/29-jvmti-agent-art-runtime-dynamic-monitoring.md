---
title: "26.29 JVMTI Agent — ART 运行时动态监控的实验入口与证据边界"
chapter: "26.29"
status: finalized
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
tags: [JVMTI, ART, runtime-monitoring, dynamic-instrumentation, profilo, method-tracing]
related_chapters: ["26.21", "26.23", "26.27", "1.35", "14.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "Clippings参考书+AOSP源码+章节深挖"
last_verified: "2026-07-29"
confidence: medium
sources:
  - type: aosp
    path: "art/openjdkjvmti/events.cc (android-17.0.0_r1) — 经由本卷 [1.35] 交叉引用"
  - type: aosp
    path: "art/openjdkjvmti/deopt_manager.cc (android-17.0.0_r1) — 经由本卷 [1.35] 交叉引用"
  - type: aosp
    path: "art/openjdkjvmti/ti_redefine.cc (android-17.0.0_r1) — 经由本卷 [1.35] 交叉引用"
  - type: aosp
    path: "art/runtime/instrumentation.h / instrumentation.cc (android-17.0.0_r1) — 经由本卷 [26.23] 交叉引用"
  - type: aosp
    path: "tools/base/profiler/native/perfa/perfa.cc + memory/memory_tracking_env.cc (Android Studio 源码树 platform/tools/base) — 经由本卷 [14.1] 交叉引用"
  - type: official
    path: "https://developer.android.com/studio/profile/record-java-kotlin-allocations — 经由本卷 [14.1] 交叉引用"
  - type: article
    path: "技术文章/source/juejin-android/2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md"
last_body_apply_at: "2026-07-24T07:15:55+08:00"
last_body_apply_run_id: "20260724-071534-2a71a09c"
last_body_apply_source: "source-index:91"
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
reviewed_date: "2026-07-30"
reviewed_by: hermes-aiw-review-finalize-apply
last_review_finalize_at: "2026-07-30T14:10:00+08:00"
last_review_finalize_run_id: "20260730-140532-12094eb9"
last_rework_at: "2026-07-29T14:25:42+08:00"
last_rework_run_id: "20260729-142542-rework-afd64006"
rework_resolution: "第四轮 rework：从本卷已验证章节 [1.35][14.1][26.23] 引入 AOSP android-17.0.0_r1 源码级 JVMTI 交叉引用（events.cc / deopt_manager.cc / ti_redefine.cc / instrumentation.h），解决唯一来源为 Android CLI 博文的问题；CLI 材料降级为实验工具节；标题保持但副标题已明确为实验入口与证据边界。confidence 从 low 提升至 medium。"
---

# 26.29 JVMTI Agent — ART 运行时动态监控的实验入口与证据边界

[结构参考: Clippings/线上疑难问题该如何排查和跟踪？-Android开发高手课-极客时间 53.md]

## 本节定位

JVMTI（JVM Tool Interface）是 JDK 5 / JSR-163 定义的标准工具接口。ART 从 Android 8.0（API 26）起正式支持 JVMTI，使运行时调试和性能监控类工具可以通过 agent 机制接入虚拟机。[已验证: 经由本卷 [14.1] 交叉引用 + 官方文档 Record Java/Kotlin Allocations]

本章把 JVMTI Agent 在 Android 上的内容组织为两层：

1. **ART 中 JVMTI 的源码级语义**——交叉引用本卷已验证章节 [1.35]（ART 去优化）和 [14.1]（Android Studio Profiler），这些章节已基于 `android-17.0.0_r1` AOSP 源码做过逐文件验证。
2. **Android CLI 作为实验准备工具**——唯一原始材料是 Android CLI 预览版博文，它能安全支撑的是实验工程生成、SDK 管理和 UI 取证，不能替代 JVMTI 运行时机制本身的源码核验。

## ART 中 JVMTI 的源码级语义

> 以下内容交叉引用本卷已验证章节，所有 AOSP 源码路径均已在对应章节中以 `android-17.0.0_r1` tag 验证。

### JVMTI Agent 注入路径

Android Studio Memory Profiler 的分配追踪数据通路展示了 Android 上 JVMTI agent 的实际注入方式：device 端的 JVMTI agent（`libperfa.so`）由 Android Studio 推送到 `/data/local/tmp/perfd/perfd` daemon，再通过 `am attach-agent` 注入目标应用，随后注册 `JVMTI_EVENT_VM_OBJECT_ALLOC` / `OBJECT_FREE` / `GARBAGE_COLLECTION_START` / `GARBAGE_COLLECTION_FINISH` / `CLASS_PREPARE` 等事件回调获取运行时数据。[已验证: 本卷 [14.1]，源码 `tools/base/profiler/native/perfa/perfa.cc` + `memory/memory_tracking_env.cc`，Android Studio 源码树 `platform/tools/base`]

这直接回答了 "线上 attach/detach 是否可用" 的问题：**Android 通过 `am attach-agent` 支持运行时 agent attach，但要求目标 App 处于 debuggable 状态**。当 App 仅配置 `android:profileable="true"`（非 debuggable）时，JVMTI 路径完全不可用——MEMORY_HEAP_DUMP / MEMORY_JVM_RECORDING / MEMORY_GC / MEMORY_LEAK_WITH_LEAKCANARY 四项 Memory Profiler 功能被禁用（`SupportLevel.kt:39-46` PROFILEABLE except 列表），只保留实时内存曲线与 Perfetto heapprofd 的 native allocation。[已验证: 本卷 [14.1]]

### JVMTI 事件与 ART Instrumentation 的映射

ART 的 JVMTI 实现位于 AOSP 源码 `art/openjdkjvmti/` 目录。API 37 的 JVMTI 事件与 deopt（去优化）需求有明确映射关系，验证自 `openjdkjvmti/events.cc` 与 `openjdkjvmti/deopt_manager.cc`：[已验证: 本卷 [1.35]，源码 `art/openjdkjvmti/events.cc` + `art/openjdkjvmti/deopt_manager.cc`（android-17.0.0_r1）]

| JVMTI 事件类别 | deopt 需求 | 源码依据 |
| --- | --- | --- |
| breakpoint、exception、method entry/exit | limited requirement（受限路径） | `openjdkjvmti/events.cc` |
| exception catch（全局监听） | full deopt（全局解释器） | `openjdkjvmti/events.cc` |
| field access/modification、single-step、frame-pop、force-early-return | 有目标线程→线程级；无目标线程→full deopt | `openjdkjvmti/deopt_manager.cc` |
| class load、compiled method load、GC 事件 | 不要求 deopt | `openjdkjvmti/events.cc` |

关键结论：**"启用任意 JVMTI agent 就会让全进程永久解释执行"不成立**。应根据 agent 实际启用的事件类型和线程过滤器判断 instrumentation level。[已验证: 本卷 [1.35]]

### DeoptManager 的三种作用域

ART 通过 `DeoptManager`（`openjdkjvmti/deopt_manager.cc`）将 JVMTI 请求映射为三个级别的 instrumentation：[已验证: 本卷 [1.35]，源码 `art/runtime/instrumentation.cc` + `art/openjdkjvmti/deopt_manager.cc`（android-17.0.0_r1）]

| Instrumentation Level | 行为 | 适用场景 |
| --- | --- | --- |
| `kInstrumentNothing` | 无 entry/exit hook 要求 | 无 agent 或仅注册 GC/class-load 事件 |
| `kInstrumentWithEntryExitHooks` | 运行 method entry/exit hooks，仍可执行支持 hook 的 compiled code | method tracing、breakpoint（非全局） |
| `kInstrumentWithInterpreter` | 安装 interpreter stubs，强制方法进入解释器 | exception catch 全局监听、field access 全局监听 |

- **方法级 deopt**：`Instrumentation::Deoptimize(method)` 把方法 entrypoint 改为 quick-to-interpreter bridge，可撤销。普通非 native、非 proxy 方法上的 breakpoint 走此路径。[已验证: 本卷 [1.35]]
- **线程级 deopt**：部分 JVMTI 事件（single-step、field access/modification、frame-pop、force-early-return）允许指定线程，`DeoptManager` 通过 `RequestSynchronousCheckpoint()` 在目标线程上增加 force-interpreter count。[已验证: 本卷 [1.35]]
- **全局 deopt**：`Instrumentation::DeoptimizeEverything(key)` 请求 `kInstrumentWithInterpreter`，JIT 编译入口会因 `AreAllMethodsDeoptimized()` 返回 true 而跳过方法编译。[已验证: 本卷 [1.35]]

### 类重定义（RedefineClasses）

JVMTI 支持运行时类重定义，实现在 `openjdkjvmti/ti_redefine.cc`。API 37 区分两种情况：[已验证: 本卷 [1.35]，源码 `art/openjdkjvmti/ti_redefine.cc`（android-17.0.0_r1）]

- **非结构性 redefinition**：为旧方法建立 obsolete method，修正活动栈 method 指针，更新 JIT 数据。代价较小。
- **结构性 redefinition**（改变字段或方法布局）：强制每个线程每个可去优化 frame 设置 redefinition flag，替换 class/instance 引用，调用 `InvalidateAllCompiledCode()` 清空 JIT compiled code。代价很大。

Android Studio 的 "Apply Changes" 最终走哪条路径取决于修改内容和部署机制，不能把每次 Apply Changes 都描述为结构性全量 deopt。[已验证: 本卷 [1.35]]

### 与字节码插桩和 XTrace 的选型关系

本章既有提纲把 JVMTI、字节码插桩和 XTrace 放在同一组选型问题里：[来源: 本章既有提纲]

| 方案 | 时机 | 侵入性 | 详见章节 |
| --- | --- | --- | --- |
| 字节码插桩（ASM/AGP） | 编译期 | 需要特殊构建；覆盖率依赖编译期决定 | [26.21] |
| XTrace（ART hook） | 运行时 | 非侵入式动态追踪，利用 ART Instrumentation listener | [26.23] |
| JVMTI Agent | 运行时 | 通过标准 agent 接口 attach；受 debuggable 约束 | 本章 |

ART Instrumentation 子系统（`art/runtime/instrumentation.h`）的 `InstrumentationListener` 定义了 `MethodEntered`、`MethodExited`、`MethodUnwind`、字段读写等回调接口。JVMTI 事件和 XTrace 的 method tracing 最终都汇入这套 Instrumentation 机制。[已验证: 本卷 [26.23]，源码 `art/runtime/instrumentation.h`（android-17.0.0_r1）]

详见 [26.23 XTrace — 生产级 ART 动态方法追踪] 对 ART Instrumentation listener 机制的完整分析，以及 [26.21 编译期字节码插桩与监控自动化] 对编译期插桩的讨论。

## Android CLI 作为实验准备工具

> 本节的唯一原始材料是 Android CLI 预览版博文（掘金，2026-04-21），它描述的是 Agent/CI 工作流的流程入口能力，不是 ART JVMTI 运行时机制的一手证据。以下内容仅作为 JVMTI 实验的环境准备和取证工具参考。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

### Android CLI 能安全支撑什么

材料把 Android CLI 描述为 Android 团队发布的预览版命令行入口，强调它面向 Agent 工作流，提供项目模板、SDK 管理、设备/界面操作、文档检索和 skills 安装等能力；这些能力适合放在 JVMTI 排障链路的"准备与取证"层。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

在本章范围内，它可以安全承担三类工作：

1. **显式化实验工程**：材料给出 `android create list`、`android create --dry-run --verbose empty-activity-agp-9` 和 `android create -o ./DemoApp empty-activity-agp-9`。这些命令适合记录样例工程从 dry-run 到落盘的过程，避免 Agent 临时拼 Gradle、目录和模板。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]
2. **显式化 SDK 与设备前置条件**：材料说明 `android sdk install` 可指定包名、版本或渠道，并给出 `android sdk install platforms/android-34 build-tools/34.0.0` 与 `android sdk list 'platforms/.*'` 示例。它们适合记录实验需要的 SDK 包和已安装平台，降低"装错版本、路径混乱、隐式依赖"的复现风险。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]
3. **显式化 UI 触发与外部证据**：材料列出 `android screen capture --annotate`、`android screen resolve --screenshot=ui.png --string="input tap #5"` 和 `android layout --diff`。这些命令适合把方法追踪或字段观察实验中的外部触发动作、截图和布局变化留作验收证据。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

### Agent 工作流中的使用边界

材料提到 `android init` 会安装 `android-cli` skill，帮助 Agent 理解并使用 Android CLI；还提到 `android skills list --long`、`android skills find 'performance'`、`android skills add --agent='gemini' edge-to-edge` 这类命令可管理 Markdown 形式的工作流指令集。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

接入 JVMTI 研究时，需要保留两条边界：

- **skills 约束操作，不替代源码核验**：`android docs search` / `android docs fetch` 可以作为官方知识检索入口，帮助定位推荐做法或文档主题；但 ART JVMTI capability 子集、attach 生命周期、事件语义、对象 tag 行为和卸载清理仍要以 android-17.0.0_r1 源码与可复现实验为准（参见上文已交叉引用的源码级结论）。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]
- **预览版工具不扩大版本边界**：材料把 Android CLI 标为"预览版"，示例中出现 `platforms/android-34`，不能据此推出 Android 18/API 38 及之后的运行时结论。AIW 当前主线仍限定在 Android 17.0.0_r1 / API 37 及 android17-6.18 内核基线。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md]

### 建议的 JVMTI 实验记录模板

当用 Agent 协助验证 JVMTI Agent 或 ART 运行时监控时，建议至少保留下面四层证据。这样即便不深入 `attachAgent`、事件回调或对象 tag 的实测，也能为后续源码复核和实测留下可复现入口。

| 证据层 | 建议记录项 | 作用 |
| --- | --- | --- |
| 工程生成 | `android create --dry-run --verbose ...` 与实际 `android create -o ...` 输出 | 证明样例工程如何生成，便于回看模板、Gradle 配置和初始文件差异。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| SDK 环境 | `android sdk install ...` 与 `android sdk list 'platforms/.*'` 输出 | 证明实验所需平台和 build-tools，不把环境问题误判为 JVMTI 行为差异。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| 设备/UI 触发 | `android screen capture --annotate`、`android screen resolve ...`、`android layout --diff` 输出 | 证明触发路径和界面状态，方便把外部操作与运行时观测时间线对齐。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |
| 知识检索 | `android docs search ...` 与 `android docs fetch ...` 输出 | 作为官方文档导航线索；最终运行时结论仍需源码和实测确认。[来源: 2026-07-24-76308345-Android CLI 来了！终端一键建项目、控模拟器、给 Agent.md] |

## 后续源码实测清单

以下条目保留为后续实测清单，本章通过交叉引用已建立源码级语义映射，但尚未独立提供可复现的端到端实测记录：

- `android.os.Debug.attachAgent` 在 Framework/API 层的入口、权限和错误处理边界——本章通过 [14.1] 确认了 `am attach-agent` 路径和 debuggable 约束，但 `Debug.attachAgent` 公共 API 的详细权限模型需进一步验证。[交叉引用: 本卷 [14.1]]
- `Agent_OnLoad` / `Agent_OnUnload` 在 ART 加载与清理链路中的调用条件——本章通过 [1.35] 确认了 DeoptManager 和 instrumentation level 机制，但 agent 生命周期回调本身需独立核验。[交叉引用: 本卷 [1.35]]
- MethodEntry/MethodExit 与 FieldAccess/FieldModification 事件的 capability 条件——本章通过 [1.35] 给出了事件→deopt 映射表，已建立框架性结论。[交叉引用: 本卷 [1.35]]
- TagObject/GetObjectsWithTags 这类对象标记能力在泄漏检测或堆对象归因中的可用边界——本章通过 [14.1] 确认了 `VM_OBJECT_ALLOC` / `OBJECT_FREE` 事件用于分配追踪的路径，但 TagObject 需独立验证。[交叉引用: 本卷 [14.1]]
- 线上 attach/detach 是否可用、可控和可回滚——本章已通过 [14.1] 确认 profileable（非 debuggable）App 的 JVMTI 不可用约束；release build 线上 attach 的安全策略需结合签名、SELinux/权限与应用发布策略单独验证。[交叉引用: 本卷 [14.1]]

## 复查结论

> **第五轮 review-finalize（2026-07-30）：`rework-verified` → `finalized`**

本轮深度复核逐项核验了章节交叉引用与源码一致性，全部通过，推进为 finalized。

核验结论：

1. **事件→deopt 映射表**（line 71-76）：与 [1.35] line 215-219 完全一致——breakpoint/exception/method-entry-exit 为 limited；exception-catch 全局监听为 full deopt；field access/modification、single-step、frame-pop、force-early-return 有目标线程→线程级、无目标线程→full deopt；class load/compiled method load/GC 不要求 deopt。
2. **DeoptManager 三种作用域**（line 84-92）：与 [1.35] line 187-213 一致——`kInstrumentNothing` / `kInstrumentWithEntryExitHooks` / `kInstrumentWithInterpreter`，方法级/线程级/全局 deopt 机制。
3. **RedefineClasses**（line 96-101）：与 [1.35] line 239-250 一致——非结构性 vs 结构性 redefinition，`InvalidateAllCompiledCode()`。
4. **Agent 注入路径**（line 63-65）：与 [14.1] line 169/173 一致——`libperfa.so` → `/data/local/tmp/perfd/perfd` → `am attach-agent`，`SupportLevel.kt:39-46` profileable 约束。
5. **InstrumentationListener 回调**（line 113）：与 [26.23] line 57-60 一致——`MethodEntered` / `MethodExited` / `MethodUnwind`。
6. **版本边界**：所有结论限定 android-17.0.0_r1 / API 37；CLI 示例 `platforms/android-34` 明确标注不扩大版本边界。
7. **来源结构**：6 个 AOSP/official 源码 + 1 个 article 材料分层标注，article 材料正确降级为"实验准备工具"节。

置信度从 medium 评估后维持——交叉引用章节 [1.35] (confidence: high) 和 [14.1] (confidence: high) 均已 finalized/verified，可充分支撑本章源码级结论。Android CLI 实验工具节作为流程入口参考，不承担运行时机制断言。剩余 5 项后续源码实测清单诚实标注了需独立验证的边界（`Debug.attachAgent` 权限模型、`Agent_OnLoad/OnUnload` 生命周期、TagObject 等），不影响已确立的框架性结论的正确性。

> **第四轮 rework（2026-07-29）：`needs-rework` → `rework-verified`**

本次 rework 的核心修复：从本卷已验证章节 [1.35][14.1][26.23] 引入 AOSP `android-17.0.0_r1` 源码级 JVMTI 交叉引用，解决了前三轮复核中"唯一来源为 Android CLI 博文，无法支撑源码级结论"的问题。

具体改进：

1. **新增"ART 中 JVMTI 的源码级语义"节**：包含 JVMTI agent 注入路径（`am attach-agent` + `libperfa.so`）、事件→deopt 映射表（`openjdkjvmti/events.cc`）、DeoptManager 三种作用域（`deopt_manager.cc`）、类重定义（`ti_redefine.cc`），全部交叉引用本卷已验证章节，标注 AOSP 源码路径。
2. **Android CLI 材料降级**：保留为"实验准备工具"节，明确其证据边界（流程入口而非运行时机制一手来源）。
3. **后续源码实测清单更新**：标注每项已通过交叉引用建立的结论范围和仍需独立实测的边界。
4. **选型对比表**：新增 JVMTI / 字节码插桩 / XTrace 三方选型表，交叉引用 [26.21][26.23]。

剩余风险（维持追踪）：

- 本章 JVMTI 语义全部来自对本卷其他章节的交叉引用，尚未在本章内部独立进行 AOSP 源码逐行核验和端到端实测。若引用章节被修改，本章结论受影响。
- TagObject/GetObjectsWithTags 对象标记能力的具体实现边界未在任何已验证章节中展开。
