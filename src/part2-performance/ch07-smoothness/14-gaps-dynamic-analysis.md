---
title: "GAPS：Android 动态分析目标可达性路径重建"
chapter: "7.14"
section: "7.14"
status: ready-for-review
applicable_versions: "论文实验环境：Android 13 x86-64 emulator；ARM 场景：Pixel 2 Android 11"
tags: [dynamic-analysis, gui-testing, static-analysis, method-reachability, android-testing]
related_chapters: ["7.3", "7.4", "13.1", "13.3"]
created_by: "openclaw-task2a"
created_date: "2026-04-10"
gap_source: "研究素材"
confidence: medium
last_verified: "2026-04-21"
last_verified_against: "arXiv 2511.23213 v2, ACM paper text, samudoria/GAPS README"
sources:
  - type: paper
    path: "https://arxiv.org/abs/2511.23213"
    title: "Mind the GAPS: Bridging the GAPS between Targeted Dynamic Analysis and Static Path Reconstruction in Android Apps"
    authors: "Samuele Doria, Eleonora Losiouk"
    date: "2025-11-28"
  - type: repo
    path: "https://github.com/samudoria/GAPS"
    title: "samudoria/GAPS"
pipeline_stage: task6_pending
task6_state: reviewed
task6_result: pass-light-edit
task9_state: pending
task9_result: needs-rework
task2b_state: fixed
task2b_result: fixed
reviewed_date: "2026-04-22"
reviewed_by: openclaw-task6
review_type: "task6-writing-quality-review"
repaired_date: "2026-04-21"
repaired_by: "openclaw-task2b"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-04-21"
last_task9_at: "2026-04-21T15:34:18+08:00"
---

# 7.14 GAPS：Android 动态分析目标可达性路径重建

## 开篇：为什么了解这个

GAPS 处理的是一个很具体的问题：给定一个目标方法，怎样在 Android 应用里尽量稳定地把它跑到。纯 GUI tester 往往只能盲扫界面，静态分析又容易在全程序 call graph 上付出很高代价。GAPS 把两条路线接起来，先从目标方法反向重建可行路径，再把路径翻成运行期可以执行的入口和界面操作。

这篇论文和仓库更适合被当成“目标方法可达性工具链”，不是现成的 Perfetto 性能分析框架。论文验证的是路径重建和方法触达率，性能 trace 只是后续可以外接的观测手段。

## 要点

### 🔹 目标可达性问题：静态与动态要分开看

- **静态路径重建**：GAPS 在 AndroTest 上能为 **88.24%** 的目标方法生成至少一条路径。这里的对比基线是 **FlowDroid 58.81%**、**DroidReach 9.48%**。这组数据衡量的是“能不能从静态分析阶段找出可行路径”。
- **动态方法触达**：GAPS 在同一基准上的动态触达率是 **57.44%**。这一组的对比对象是 GUI tester，分别是 **Guardian 17.12%**、**APE 12.82%**、**GoalExplorer 9.69%**。这组数据衡量的是“运行期有没有真的把目标方法跑到”。
- **实验口径**：AndroTest 为 56 个开源应用随机挑选每个应用 50 个目标方法，动态实验统一给 5 分钟超时。把静态 88.24% 和 APE 的 12.82% 放在同一句里，会把两组不同实验维度混在一起。

### 🔹 GAPS 的主链：目标方法 → 路径 → 指令 → 动态执行

GAPS 的论文主线可以按下面这条链理解：

1. **从目标方法反向遍历调用关系**  
   GAPS 不先构建全程序 call graph，而是从目标方法做 backward traversal，只保留和该目标相关的局部调用图。论文把这条路径写成 target-oriented、context-sensitive 的 partial call graph。

2. **补齐入口、条件和 GUI 触发点**  
   在局部调用图里，GAPS 会继续做 points-to analysis 和 constant propagation，处理三类关键信息：
   - 这个目标方法能从哪个 entry point 进入
   - 哪些条件分支必须先满足
   - 哪个 `Activity` 里的哪个 GUI 元素会触发后续调用

3. **把结果落成 JSON 指令**  
   静态阶段的输出会直接落成可以执行的高层指令。指令里会带上 entry point、Activity 名称、resource ID 和对应的调用序列。

4. **运行期按指令驱动应用**  
   论文 6.3 的实现使用 AndroidViewClient 通过 `findViewById()` / `touch()` 去点击静态阶段找到的控件，按路径推进界面状态。Frida 是可选组件，用来在目标方法上挂 hook，确认方法是否真的被执行。

5. **找不到控件时再交给 Guardian 兜底**  
   论文写得很明确，Guardian 是 fallback，不是默认主链。只有当 GAPS 预期的 Activity 或 widget 没出现在当前界面时，才把交互暂时交给 Guardian，等界面回到预期路径后再继续按静态指令执行。

公开仓库当前的 `run` 模式又加入了 built-in LLM agent，会先读取界面层级，再给出点击、输入、返回等动作。这属于仓库后续演进。写论文实验设定时，应以论文 6.3 和对应实现边界为准，不把它写成 Android Instrumentation 或 Perfetto 验证链。

### 🔹 UI 资源 ID 逆向与 GUI 操作序列生成

GAPS 静态阶段会把 GUI 事件解析成运行期可用的操作线索，主要有三步：

- **用 Androguard 读 APK/DEX**：拿到方法分析结果和 smali 指令。
- **用 Apktool 还原资源 ID**：把 `findViewById()` 里的整型资源值，通过 `public.xml` 还原成字面量 ID。
- **把路径翻成高层交互指令**：输出 `Activity + resource ID + action` 这类 JSON 指令，供动态阶段直接使用。

这一步决定了静态结果能否落到运行期操作。

### 🔹 Perfetto 是衍生观测手段，不是论文核心组件

原始论文的可达性验证主链里没有把 Perfetto 当成核心组件。

- **AndroTest 基准**：论文使用 AndroLogs 对应用做 instrumentation，通过日志判断目标方法是否被执行。
- **真实应用实验**：论文在 Google Play Top 50 场景里改用 Frida hook 目标方法，因为 AndroLogs 无法稳定重打包真实应用。
- **Perfetto 的位置**：如果后续要把 GAPS 接进性能分析工作流，Perfetto 可以作为额外观测面，用来关联某次路径触发后的主线程、FrameTimeline、调度或 I/O 行为。但这已经超出论文原始验证链。

更稳的用法是：先用 GAPS 把场景稳定驱到目标方法附近，再用 Perfetto、simpleperf、Frida 或应用自定义 trace marker 做二次观测。不要把 Perfetto 写成 GAPS 论文里的默认 reachability validator。

### 🔹 与 FlowDroid、DroidReach 和 GUI tester 的区别

- **FlowDroid**：擅长全程序数据流/污点分析，代价是 call graph 构建重，论文实验里静态路径生成率为 **58.81%**，平均 **35.06 秒/应用**。
- **DroidReach**：同样做静态路径重建，但依赖完整 call graph，论文实验里路径生成率只有 **9.48%**，平均 **23.46 秒/应用**。
- **APE / Guardian / GoalExplorer**：属于运行期 GUI 探索工具，优势是能直接操作界面，短板是对“指定目标方法”缺少静态路径引导。
- **GAPS**：用静态路径约束运行期搜索范围，静态阶段 **88.24%**、平均 **4.27 秒/应用**，动态阶段 **57.44%**，比纯 GUI tester 更容易收敛到目标方法。

### 🔹 放到性能分析工作流里时，边界要先写清楚

GAPS 对性能工程有潜在价值，但这部分要按“衍生场景”来写：

- 可以用来**稳定重放某个可疑方法的触发路径**，减少手工点点点。
- 可以用来**把 trace 抓取点前置到目标方法附近**，让 Perfetto 或 simpleperf 更容易卡住问题窗口。
- 如果目标是 **jank / ANR / 回归测试**，还需要额外设计 trace marker、hook、统计口径和失败回退策略。论文没有直接给出这部分实验结果。

## 扩展

### 🔸 Android 动态分析工具全景

- **APE**：偏模型驱动和大范围 GUI 探索。
- **Guardian**：偏 LLM 驱动的语义化界面探索。
- **GoalExplorer**：先建 Screen Transition Graph，再引导 Stoat 做动态探索。
- **GAPS**：把目标方法可达性当成第一目标，静态路径重建先于动态交互。

### 🔸 论文验证环境与仓库边界

- **静态分析环境**：CloudLab Ubuntu 22.04，64GB RAM。
- **动态分析环境**：Android 13 x86-64 emulator；需要 ARM 时使用 Pixel 2 Android 11。
- **超时设置**：动态实验统一 5 分钟。
- **仓库边界**：README 说明 `run` 模式默认可用 built-in LLM agent；论文正文则以 AndroidViewClient + optional Guardian + optional Frida 描述实验链。引用实现时要说明“论文基线”还是“当前仓库版本”。

### 🔸 局限性：哪些场景会掉精度

- **Jetpack Compose**：论文明确写了当前不支持 Compose。
- **Flutter / React Native**：逻辑不完全落在传统 Dalvik 调用链里，静态路径重建会受限。
- **混淆、反射、复杂 app state**：真实应用里的 path explosion、账号态、支付流、系统权限广播都会降低动态触达率。
- **性能分析扩展**：若要把它用于 jank/ANR 排查，还要自己补 trace 与统计口径。

## 参考资料

### 论文与仓库

- arXiv: Mind the GAPS: Bridging the GAPS between Targeted Dynamic Analysis and Static Path Reconstruction in Android Apps  
  https://arxiv.org/abs/2511.23213
- samudoria/GAPS  
  https://github.com/samudoria/GAPS

### 论文里直接提到的实现与依赖

- AndroidViewClient  
  https://github.com/dtmilano/AndroidViewClient
- Frida  
  https://frida.re/
- Apktool  
  https://apktool.org/
- Androguard  
  https://github.com/androguard/androguard
- AndroLog: Android Instrumentation and Code Coverage Analysis  
  https://arxiv.org/abs/2404.11223
