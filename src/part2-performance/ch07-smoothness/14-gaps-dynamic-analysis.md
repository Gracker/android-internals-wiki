---
title: "GAPS：Android 动态分析目标可达性路径重建"
chapter: "7.14"
section: "7.14"
status: "finalized"
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
  - type: repo
    path: "https://github.com/samudoria/GAPS"
    authors: "Samuele Doria, Eleonora Losiouk"
    date: "2025-11-28"
task6_state: reviewed
task6_result: "pass-light-edit"
reviewed_date: "2026-06-19"
reviewed_by: "openclaw-task6"
task6_reviewed_date: "2026-06-19"
last_task6_at: "2026-06-19T12:09:00+08:00"
auto_promoted_date: "2026-06-05"
auto_promoted_by: "openclaw-task6"
last_task6_audit: "2026-05-23"
review_type: "task6-writing-quality-review"
repaired_date: 2026-05-05
repaired_by: openclaw-task2b
review_round: 3
task9_result: auto-fixed
task9_state: reviewed
task2b_state: fixed
task2b_result: fixed
pipeline_stage: ready-to-publish
task9_reviewed_date: "2026-05-24"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-24T10:22:45+08:00"
last_task9_audit: "2026-06-19"
task2b_fixed_date: "2026-06-05T02:50:00+08:00"
task2b_fixed_by: "openclaw-task2b-main"
task2b_fix_summary: "Removed unsupported reflection/DI/dynamic-proxy penetration rate table (not backed by GAPS paper/repo per Task9 idle audit 2026-05-24); replaced with qualitative Limitations-based description consistent with paper text."
task9_review_notes: "2026-05-05 01:36 task9 deep-review: needs-rework。P0 1 / P1 1 / P2 0；详见 logs/deep-review/2026-05-05-01-deep-review.md。；2026-05-05 02:37 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0。Frida trace marker 与 Perfetto SDK 边界已处理完成；自动晋升 finalized。；2026-05-24 10:22 task9 idle-audit: needs-rework。P0 0 / P1 1 / P2 0。L196-L212 的反射/DI/动态代理穿透率表未被 GAPS 论文/仓库支撑，已写入 queue。；2026-06-19 Task9 idle-audit auto-fix：修正 GAPS Limitations 来源归因，反射/DI/动态代理/JNI 仅保留为外推风险；回到 Task6 复审。"
review_notes: "2026-05-05 Task6：补齐 outline 块，修正 frontmatter 结构、标题标点和少量中英文间距；L1/L2 通过，等待 Task9 复审技术项。 | 2026-06-19 Task6 revisit: Task9 auto-fix 修正 Limitations 来源归因后复审；L1 禁用词/格式零命中，L2 可读性通过；修正 frontmatter 重复 task6_state；无 B 类大问题；自动晋升 finalized。"
last_task9_audit_at: "2026-06-19T10:27:25+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-19-10-audit.md"
last_task9_autofix_at: "2026-06-19"
---

# 7.14 GAPS：Android 动态分析目标可达性路径重建

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 目标可达性问题：静态与动态要分开看
- 🔹 GAPS 的主链：目标方法 → 路径 → 指令 → 动态执行
- 🔹 UI 资源 ID 逆向与 GUI 操作序列生成
- 🔹 Perfetto 是衍生观测手段，不是论文核心组件
- 🔹 与 FlowDroid、DroidReach 和 GUI tester 的区别
- 🔹 放到性能分析工作流里时，边界要先写清楚

### 扩展（可选深入）

- 🔸 Android 动态分析工具全景
- 🔸 GAPS 与 LLM 驱动测试的对比
- 🔸 用 Frida hook 实现目标触达即抓 Trace
- 🔸 论文验证环境与仓库边界
- 🔸 局限性：哪些场景会掉精度
<!-- outline-end -->

## 为什么要了解 GAPS

GAPS 处理的是一个很具体的问题：给定一个目标方法，怎样在 Android 应用里尽量稳定地把它跑到。纯 GUI tester 往往只能盲扫界面，静态分析又容易在全程序 call graph 上付出很高代价。GAPS 把两条路线接起来，先从目标方法反向重建可行路径，再把路径翻成运行期可以执行的入口和界面操作。

这篇论文和仓库更适合被当成"目标方法可达性工具链"，不是现成的 Perfetto 性能分析框架。论文验证的是路径重建和方法触达率，性能 trace 只是后续可以外接的观测手段。

## 要点

### 🔹 目标可达性问题：静态与动态要分开看

- **静态路径重建**：GAPS 在 AndroTest 上能为 **88.24%** 的目标方法生成至少一条路径。这里的对比基线是 **FlowDroid 58.81%**、**DroidReach 9.48%**。这组数据衡量的是"能不能从静态分析阶段找出可行路径"。
- **动态方法触达**：GAPS 在同一基准上的动态触达率是 **57.44%**。这一组的对比对象是 GUI tester，分别是 **Guardian 17.12%**、**APE 12.82%**、**GoalExplorer 9.69%**。这组数据衡量的是"运行期有没有真的把目标方法跑到"。
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

   **入口与隐式调用边的建模**是这一步的核心难点。Android 应用的调用图不像普通 Java 程序那样可以从 `main()` 出发。GAPS 在这一步要处理三类隐式边：

   - **生命周期回调**：`Activity.onCreate()`、`Fragment.onResume()` 等入口由系统框架调用，不会出现在显式 call graph 里。GAPS 通过 AndroidManifest 解析和 Soot 框架的虚拟边(virtual edges)把它们接进调用图。
   - **UI 回调**：`View.OnClickListener.onClick()`、`AdapterView.OnItemSelectedListener.onItemSelected()` 等通过 `setOnClickListener()` 注册的回调。GAPS 使用 EdgeMiner 的回调映射规则，把 `setOnClickListener(this)` 里的 `this` 绑定到对应的 `onClick()` 实现。
   - **ICC(Inter-Component Communication)**：`startActivity(intent)`、`startService(intent)` 等。GAPS 在 smali 层分析 Intent 构造参数，结合 AndroidManifest 中的 intent-filter 声明推断目标 Component。对于隐式 Intent，需要匹配 action、category、data URI；对于显式 Intent，直接从 `setClassName()` 或 `setComponent()` 读取目标。

   这三类隐式边解决的是同一个问题：从静态分析角度看，Android 应用的“入口”不是一个点，而是一组由系统框架和用户交互驱动的分散入口。GAPS 的静态阶段要把目标方法反向追溯到这些入口中的某一个，再把入口翻成运行期可执行的 `adb am start` 命令或 UI 操作指令。

3. **把结果落成 JSON 指令**
   静态阶段的输出会直接落成可以执行的高层指令。指令里会带上 entry point、Activity 名称、resource ID 和对应的调用序列。

4. **运行期按指令驱动应用**
   论文 6.3 的实现使用 AndroidViewClient 通过 `findViewById()` / `touch()` 去点击静态阶段找到的控件，按路径推进界面状态。Frida 是可选组件，用来在目标方法上挂 hook，确认方法是否真的被执行。

5. **找不到控件时再交给 Guardian 兜底**
   论文写得很明确，Guardian 是 fallback，不是默认主链。只有当 GAPS 预期的 Activity 或 widget 没出现在当前界面时，才把交互暂时交给 Guardian，等界面回到预期路径后再继续按静态指令执行。

公开仓库当前的 `run` 模式又加入了 built-in LLM agent，会先读取界面层级，再给出点击、输入、返回等动作。这属于仓库后续演进。写论文实验设定时，应以论文 6.3 和对应实现边界为准，不把它写成 Android Instrumentation 或 Perfetto 验证链。

### 🔹 UI 资源 ID 逆向与 GUI 操作序列生成

GAPS 的静态阶段会把 GUI 事件解析成运行期可用的操作线索，主要有三步：

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
- **APE / Guardian / GoalExplorer**：属于运行期 GUI 探索工具，优势是能直接操作界面，短板是对"指定目标方法"缺少静态路径引导。
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

### 🔸 GAPS 与 LLM 驱动测试的对比

2026 年 1 月的最新论文将 GAPS 与 Guardian（LLM 驱动的 GUI 测试工具）做了专项对比：

- GAPS 的动态触达率（57.44%）约为 Guardian（17.12%）的 3.4 倍。
- LLM Agent 在复杂 Activity 状态转换中容易“迷路”：重复点击已访问的界面、跳过需要特定前置条件的入口、在深层嵌套的 Fragment 导航中失去方向。
- GAPS 的静态路径重建提供的是精确的导航：每一步都有明确的 Activity、控件 ID 和操作类型。这种确定性在方法级触达场景中比 LLM 的语义化探索更有效。

GAPS 仓库的 `run` 模式集成了 LLM Agent，但定位是 fallback：当静态阶段预期的控件不存在时，LLM 尝试替代性操作。论文基线实验不依赖 LLM 组件。

这组对比的结论：在“指定目标方法并稳定触达”这个任务上，基于程序分析的路径重建仍然比大模型的界面探索更可靠。LLM 的优势在于适应性：面对 GAPS 无法建模的 Compose 界面或动态布局，LLM 有机会通过视觉理解绕过静态分析的限制。

### 🔸 用 Frida hook 实现目标触达即抓 Trace

GAPS 的 Frida hook 除了用于确认方法是否被执行，还可以扩展为“触达即抓 Trace”的触发器：

1. 在目标方法上挂 Frida hook。
2. Hook 触发时，通过 Frida `Java.use("android.os.Trace").beginSection("gaps_target")` / `endSection()` 注入自定义 trace marker。或者使用 native 层的 `ATrace_beginSection()` / `ATrace_endSection()`（需要 Frida 的 `Module.getExportByName()` 调用 `libandroid.so` 中的导出符号）。
3. Trace 抓取有两种路径：
   - **轻量级（推荐）**：预先通过 `adb shell perfetto` 启动环形缓冲区 trace 录制，Frida hook 触发时只注入 marker，后续在 Perfetto UI 中用 marker 时间点定位目标方法执行窗口。
   - **集成 Perfetto SDK**：在 App 或注入的 native 库中嵌入 Perfetto SDK 的 Producer/DataSource，通过 `perfetto::Tracing::Initialize()` 初始化后，可以在 hook 触发时启动一段自定义 DataSource 的短窗口 trace。这种方式需要提前完成 SDK 集成，不能从 Frida 脚本直接假定系统已提供该 C++ 接口。

这样做的好处是避免"抓 Trace 太晚"。全量 trace 在长时段录制中容易遗漏首帧信息，而 GAPS 的路径触达 + Frida 触发可以把 trace 窗口精确压缩到目标方法执行前后。marker 注入方案无需 App 侧代码修改，是最小侵入的实现路径。

### 🔸 论文验证环境与仓库边界

- **静态分析环境**：CloudLab Ubuntu 22.04，64GB RAM。
- **动态分析环境**：Android 13 x86-64 emulator；需要 ARM 时使用 Pixel 2 Android 11。
- **超时设置**：动态实验统一 5 分钟。
- **仓库边界**：README 说明 `run` 模式默认可用 built-in LLM agent；论文正文则以 AndroidViewClient + optional Guardian + optional Frida 描述实验链。引用实现时要说明"论文基线"还是"当前仓库版本"。

### 🔸 局限性：哪些场景会掉精度

- **Jetpack Compose**：论文明确写了当前不支持 Compose。
- **Flutter / React Native**：逻辑不完全落在传统 Dalvik 调用链里，静态路径重建会受限。
- **混淆、复杂 App state**：真实应用里的 path explosion、账号态、支付流、系统权限广播都会降低动态触达率。
- **性能分析扩展**：若要把它用于 jank / ANR 排查，还要自己补 Trace 与统计口径。



### 论文外推边界：反射与编译期生成

GAPS 论文的 Limitations 节只支撑几类边界：Flutter / React Native、混淆导致的 path explosion、库中的 dead code、未建模的 implicit flows、Jetpack Compose、复杂交互状态，以及 intent-filter 权限或 data 参数。反射、Dagger/Hilt、动态代理和 JNI 属于 Android 静态分析的通用风险；论文没有给出 GAPS 对这些场景的分项实验或穿透率，不能写成论文结论。

- **反射 / 动态代理**：目标调用可能在运行时由字符串、代理类或 `InvocationHandler` 拼接出来，静态 call graph 不一定能追踪到真实实现。用于 GAPS 结果解读时，只能标成待验证风险。
- **Dagger/Hilt 等编译期代码生成**：生成类存在于编译产物中，GAPS 是否能复原依赖注入关系取决于字节码形态和回调建模，论文未给出专项结果。
- **JNI / Native 调用链**：目标方法进入 native 库后，传统 Dalvik 字节码路径重建无法继续展开。论文没有对 JNI 场景给出单独实验，不能从整体 88.24% / 57.44% 推导 native 触达率。

将 GAPS 用于性能排障时，若目标方法落在这些外推场景里，应先通过 Frida hook、trace marker 或手工验证确认触达，再把 Perfetto / simpleperf 观测结果接到后续分析。

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
