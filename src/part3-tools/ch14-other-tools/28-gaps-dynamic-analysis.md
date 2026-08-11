---
title: "GAPS：Android 动态分析目标可达性路径重建"
chapter: "14.28"
section: "14.28"
status: "finalized"
applicable_versions: "论文动态实验：Android 16 x86-64 模拟器；ARM 场景：Pixel 2 / Android 11；Android 17 仅工程集成边界"
tags: [dynamic-analysis, gui-testing, static-analysis, method-reachability, android-testing]
related_chapters: ["7.3", "7.4", "13.1", "13.3"]
created_by: "openclaw-task2a"
created_date: "2026-04-10"
gap_source: "研究素材"
confidence: medium
last_verified: "2026-07-17"
last_verified_against: "arXiv 2511.23213 v3 + 论文公开复现快照 README"
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
last_task6_audit: "2026-07-06"
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
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-12
---

# 14.28 GAPS：Android 动态分析目标可达性路径重建

## 版本边界

GAPS 解决一个方法级问题：给定 APK/DEX 与目标方法，能否找出从 Android 入口到该方法的路径，并自动执行对应交互。它不负责衡量一帧是否卡顿，也不替代 Perfetto、simpleperf 或应用埋点。

以下说明依据 2026 年 7 月 17 日发布的论文 v3 与论文公开的复现快照 README。v3 已更名为 *GAPS: Targeted Execution of Android Apps via Static Path Reconstruction*，并更新了作者、实验环境、动态基线、运行时间和 PHIL agent 数据。57.44%、Guardian 17.12%、静态分析 4.27 秒及 Android 13 模拟器等早期数据均不再代表 v3。

平台集成部分以 Android 17 / API 37 / `android-17.0.0_r1` 为知识库锚点。论文自身的动态实验使用 Android 16 x86-64 模拟器；需要 ARM 时使用 Pixel 2 / Android 11。论文没有报告 Android 17 实验，论文测得的数据不能直接作为 Android 17 上的工程结论。

## 方法可达性有两个判定阶段

“静态找到路径”和“设备上执行到目标方法”是两个不同事件：

| 阶段 | 成功条件 | 不能推出的结论 |
| --- | --- | --- |
| 静态路径重建 | 至少生成一条包含目标方法的路径 | 路径在当前账号、权限和 UI 状态下一定可执行 |
| 动态目标触达 | AndroLog 或 Frida 观察到目标方法调用 | 该方法造成卡顿、ANR、耗电或安全影响 |

论文在 AndroTest 的 56 个开源应用中，每个应用固定随机选择 50 个目标方法，并让各工具使用同一组目标。只有 34.39% 的目标位于 `Activity` 中，多数目标无法通过浅层页面遍历直接命中。

v3 报告的结果如下：

### 静态路径重建

| 工具 | 生成至少一条路径的目标占比 | 平均分析时间/应用 |
| --- | ---: | ---: |
| DroidReach | 9.48% | 23.46 秒 |
| FlowDroid | 58.81% | 35.06 秒 |
| GAPS | 88.24% | 12.67 秒 |

这里的 88.24% 是路径生成率，不是路径精确率，也不能解释成 88.24% 的目标已经在设备上执行。

### 动态目标触达

| 工具 | 动态触达率 | 论文表中的平均运行时间 |
| --- | ---: | ---: |
| GoalExplorer | 4.75% | 30 分钟超时 |
| APE | 11.12% | 30 分钟超时 |
| Guardian | 34% | 30 分钟超时 |
| GAPS（关闭 PHIL） | 23.24% | 2 分 26 秒 |
| GAPS（启用 PHIL） | 56.93% | 3 分 15 秒 |

动态基线均运行三轮，每轮上限 30 分钟。GAPS 在这些实验中没有超过 5 分钟，表中的 3 分 15 秒是平均运行时间，不能写成“所有工具统一使用 5 分钟超时”。PHIL 从 23.24% 提升到 56.93% 的消融结果也说明，v3 的完整动态结果包含 agent fallback，不能再把 LLM 描述成论文实验之外的仓库附加功能。

## GAPS 的处理链

GAPS 把一次查询分成静态分析与动态执行：

`目标方法` → `目标导向的反向调用图` → `入口、条件和 GUI 触发点` → `JSON 交互指令` → `设备执行` → `运行时触达证据`

### 1. 从 APK/DEX 建立分析表示

静态阶段使用 Androguard 的 `AnalyzeAPK`/`AnalyzeDex` 读取方法、基本块和 smali 指令，并用 NetworkX 表示局部调用图。Apktool 负责恢复资源表，后续可把 smali 中的整型资源值映射为 `public.xml` 里的字面量 ID。

这条路线直接分析编译产物，不要求应用源码。代价是信息上限受 DEX、资源表、混淆和框架建模能力约束；源码中的类型语义、生成过程和运行期状态不会自动恢复。

### 2. 识别 Android 入口与 ICC

Android 应用没有单一 `main()` 入口。GAPS 会检查 manifest 中导出的组件和 intent filter，也会分析动态注册的 receiver 及相关注册路径。ICC 映射保存组件类名、action 或关联路径，供反向遍历在合法入口处停止。

论文也限定了这一步的能力：带权限的入口、系统拥有的广播，以及要求额外 data 参数的 Intent，可能有静态路径却无法自动构造出可执行输入。当前实现不能概括为已经完整求解 action、category、URI 和 extras。

### 3. 按目标反向生成局部调用图

GAPS 从目标方法向调用者反向扩展，按需构建 Class Hierarchy Analysis 图来保守解析虚调用，并在遇到已识别入口时停止该分支。它不预先构建整应用的完整 call graph。

遍历结束后，GAPS 用深度优先搜索提取入口到目标的候选路径。论文把该过程描述为 target-oriented、demand-driven、inter-procedural 和 context-sensitive。EdgeMiner 与 Soot virtual edges 提供回调映射，但未跟踪的隐式流仍会造成 call graph 不完备。

### 4. 补足条件路径

候选路径中的条件会进入 points-to analysis 与 constant propagation。v3 明确覆盖三类操作数：

- `int`、`String`、`float` 等变量和基本类型；
- 与 `null` 比较的对象；
- 方法返回值。

分析器回溯左右操作数的来源，传播候选常量，再合并能满足条件的赋值路径。这里得到的是静态可满足路径；账号态、网络返回、随机数、服务端配置等运行期输入仍可能让设备执行停住。

### 5. 找到 GUI 事件和资源 ID

GAPS 识别 `onClick()`、`onItemSelected()` 等 handler，沿 listener 注册和对象来源回溯到 `findViewById()`，再解析其资源参数。生成的 JSON 指令包含：

- 可执行入口；
- `Activity` 名称；
- 需要交互的图形元素 ID 序列；
- 对应 call sequence。

XML View 体系能提供稳定资源 ID，正好适合这套分析。Jetpack Compose 通过 Kotlin lambda 挂接事件，节点还会随 recomposition 改变；v3 的 Limitations 明确说明当前不支持 Compose。

## 动态执行：确定性指令加受限 PHIL

动态阶段安装应用，并用 AndroidViewClient 的 `findViewById()` 与 `touch()` 执行静态指令。每条候选路径开始前会重启应用，执行器持续轮询 runtime monitor。方法被观察到后返回 `REACHED`；当前路径无法继续时，转试下一条候选路径。

确定性操作遇到权限弹窗、广告或动态布局时，v3 会调用 PHIL（Predictive Handler for Interface Limitations）。它接收经过筛选的当前 GUI 层级、目标方法和静态路径，并输出 `click`、`type` 等结构化动作。论文实现使用 GPT-5.4、temperature 0.7，但 PHIL 是可关闭、可替换模型的组件，这个模型配置不属于 GAPS 的稳定接口。

PHIL 的调用受到两层约束：

- 每条路径中的同一个 `Activity` 最多介入一次；
- 障碍仍未清除，或该 `Activity` 已用过 PHIL 时，当前路径会终止。

这种约束避免 agent 无限探索，也保留了静态路径的主导地位。PHIL 仍带有非确定性，论文通过每个应用三轮运行并报告平均值来吸收部分波动。

### 当前仓库命令的含义

下面的命令展示公开复现快照中的两阶段入口，实际使用时应保存源码快照、版本标识与 `uv.lock`：

```bash
uv sync

uv run gaps static \
  -i app-under-test.apk \
  -sig 'Lcom/example/Target;->work(Ljava/lang/String;)V' \
  -cond \
  -o gaps-output

uv run gaps run \
  -i app-under-test.apk \
  -instr gaps-output/path-to-instructions.json \
  -frida
```

`static` 生成路径和高层指令，`run` 才会操作设备。`-frida` 需要运行 frida-server 的 rooted 设备或模拟器；PHIL 所用模型若要求 API 凭据，还要按快照对应的 provider 配置注入环境变量。自动化环境不应只记录“使用最新版”。

## Runtime monitor 只回答“是否触达”

论文使用了两种目标方法证据：

- AndroTest 应用可重打包，使用 AndroLog 给方法加入日志；
- 真实应用无法稳定通过 AndroLog 重打包时，使用 GAPS 的 Frida integration hook 目标方法。

这两种证据都比“页面已经打开”严格，因为页面完成不保证特定方法执行。它们仍不提供性能因果关系：一次 hook 命中没有说明方法耗时，也没有说明其调用发生在 missed frame、ANR 前兆或功耗尖峰内。

Frida hook 本身会改变执行时间。短方法、锁竞争、JIT/AOT 边界和高频调用尤其容易被探针开销污染。性能实验应把“无 hook 的基线 trace”和“带 hook 的定位 trace”分开，必要时改用应用源码中的 `Trace.beginSection()` 或 Perfetto SDK 埋点做低扰动复测。

## Perfetto 是 Android 17 工程扩展

GAPS 论文没有把 Perfetto 纳入路径生成、动态执行或 reachability 判定。把二者组合时，职责应保持分离：

| 工具 | 在组合流程中的问题 |
| --- | --- |
| GAPS 静态阶段 | 怎样从入口走到目标方法 |
| GAPS 动态阶段 | 这套交互能否执行并命中方法 |
| Frida/AndroLog/应用 marker | 目标方法在什么时间被观察到 |
| Perfetto | 同一时间窗内哪些线程、帧、调度、I/O 或 fence 出现异常 |
| simpleperf | CPU 样本主要落在哪些调用栈 |

### 一套可复现的接入顺序

1. 记录 APK SHA-256、包名、versionCode、完整 smali 方法签名与 GAPS commit。
2. 运行静态阶段，人工检查 entry point、条件和 GUI ID 是否符合目标应用。
3. 准备独立测试账号、权限、网络响应与初始数据库；记录哪些状态无法由 GAPS 生成。
4. 在交互前启动 Perfetto，配置足够长的 ring buffer，并包含目标应用的 atrace、FrameTimeline、调度、频率及场景所需数据源。
5. 安装 runtime monitor，再运行 GAPS 动态阶段。每轮同时记录 `REACHED`/`FAILED`、采用的候选路径、PHIL 是否介入和 marker 时间。
6. 只在 `REACHED` 样本内对齐目标 marker 与性能异常；`FAILED` 样本用于分析自动化可靠性，不能混入性能分位数。
7. 移除 Frida hook 后复测可疑场景，确认异常不由探针、重打包或调试环境引入。

GAPS 每试一条路径都会重启应用，这会改变进程冷热、JIT、页面缓存、数据库连接和图片缓存。若待测问题只在长会话、后台恢复或热缓存条件下出现，需要修改执行器或使用 `--manual-setup` 准备状态，不能直接沿用论文的 clean-state 策略。

### 用 Frida 注入时间锚点

下面的示例用于测试设备：它在目标 Java 方法的同一线程上包一层 `android.os.Trace` section，Perfetto 必须在 GAPS 执行前启动并采集该应用的 atrace。

```javascript
Java.perform(() => {
  const Trace = Java.use("android.os.Trace");
  const Target = Java.use("com.example.Target");
  const work = Target.work.overload("java.lang.String");

  work.implementation = function (arg) {
    Trace.beginSection("gaps_target:Target.work");
    try {
      return work.call(this, arg);
    } finally {
      Trace.endSection();
    }
  };
});
```

这个 section 包围 hook 调用期间的方法执行，可在应用线程轨道上提供时间锚点。它不负责启动或停止 Perfetto，也不能替代 FrameTimeline。目标方法若被内联、位于 native 库、存在多个 overload，或进程在 hook 安装前已执行该方法，需要调整探针并单独验证。

### jank、ANR 与功耗各看什么

- **jank**：从 missed `DisplayFrame` 与对应 `SurfaceFrame` 出发，检查 marker 是否落在相关帧的生产区间；只在时间重叠且调用链合理时继续归因。
- **ANR**：确认目标方法与主线程、binder、锁等待或 input timeout 的时序。方法命中早于 ANR 数十秒，通常还缺中间证据。
- **功耗/发热**：按同设备、同热状态、同网络条件做多轮对照；单次目标触达无法区分方法成本、PHIL 网络请求、Frida 或屏幕操作开销。
- **native 热点**：GAPS 的 DEX 路径可触达 Java/Kotlin 包装层，native 内部成本仍需 simpleperf、Perfetto native heap/CPU 数据或库内 marker。

## v3 的真实应用实验

论文还在 2026 年 6 月收集的 Google Play 下载量前 50 应用上，以 SPECK 报告的潜在安全问题方法为目标。只有 5.55% 的目标位于 `Activity` 中，场景比 AndroTest 更偏向深层代码。

| 指标 | v3 结果 |
| --- | ---: |
| 静态路径生成率 | 62.03% |
| 平均静态分析时间/应用 | 278.9 秒 |
| 生成的 call sequence | 219 条 |
| call sequence 长度 | 1—41，均值 12.42，中位数 4 |
| 三轮动态触达率均值 | 54.80% |
| 动态执行平均时间 | 4 分 48 秒 |

真实应用实验用 Frida 作为触达证据。62.03% 与 54.80% 的差值不能直接叫“静态误报率”：有些静态路径成立，但运行期需要登录、支付、特定文本、动态内容、权限或 Intent 参数，执行器没有构造出对应状态。

这些数字也不应外推为 Android 17 应用的成功率。样本、目标选择、应用版本、设备、模型和时间预算都会改变结果；Compose 在现代应用中的占比还会进一步影响 GUI ID 提取。

## 与相关工具的边界

| 工具 | 主要目标 | 输出/执行方式 | 与 GAPS 的差别 |
| --- | --- | --- | --- |
| FlowDroid | Android 污点与数据流分析 | 全程序抽象、dummy main、数据流结果 | 不生成面向目标方法的可执行 GUI 指令 |
| DroidReach | 静态路径重建 | 基于完整 call graph 输出路径 | 没有 GAPS 的动态执行、条件解析和 GUI trigger 链 |
| APE | 覆盖率导向 GUI 探索 | 模型驱动事件生成 | 不掌握目标方法的静态路径 |
| Guardian | 用户任务导向 LLM 交互 | 根据界面语义规划动作 | v3 中作为独立动态基线；不是 GAPS 内部 fallback |
| GoalExplorer | screen/activity 导向探索 | Screen Transition Graph + 动态探索 | 引导单位偏页面和 Activity，不以方法级 backward slice 为起点 |
| PHIL | GAPS 内部受限 agent | 只在确定性步骤失败时处理 UI 障碍 | 它是 GAPS v3 的 fallback，不是 Guardian 的别名 |

比较百分比时还要核对预算和分母。FlowDroid/DroidReach 的百分比属于静态路径生成，APE/Guardian/GoalExplorer/GAPS Dynamic 属于动态方法触达；把两列按高低排在一起没有统计意义。

## 已验证的限制与工程外推

论文 v3 直接列出的限制包括：

- Flutter/React Native 的主要逻辑不在传统 Dalvik 代码中；
- 混淆会引发 path explosion 并增加分析时间；
- 库中的 dead code 会拖累路径重建；
- callback mapping 未覆盖的 implicit flow 会造成 call graph unsoundness；
- 当前不支持 Jetpack Compose；
- 游戏胜利、账号、支付等复杂状态可能阻断动态执行；
- intent filter 入口可能要求权限、系统身份或额外 data；
- 动态布局和 WebView 会干扰静态 GUI 提取；
- PHIL 引入非确定性。

反射、动态代理、Dagger/Hilt、JNI 是 Android 程序分析中常见的额外风险，但论文没有提供这些类别的 GAPS 分项命中率。工程报告可以把它们列为待验证条件，不能从 88.24% 或 56.93% 推导专项能力。

Android 17 上还要额外核对：

- 目标应用是否主要采用 Compose；
- entry component 是否可从测试环境启动，权限和导出属性是否允许；
- Frida 所需 root、SELinux 与进程架构条件是否满足；
- split APK、动态特性模块和运行期代码加载是否都进入分析输入；
- 目标方法签名是否因 R8、版本更新或多 dex 布局改变。

## 复现实验检查清单

静态阶段：

- 固定论文版本、GAPS commit、Python/uv lock、Androguard 与 Apktool 版本。
- 固定 APK hash、目标签名、path limit、`-cond` 与其他 CLI 参数。
- 保存生成的 JSON、call sequence、分析时长和失败原因。

动态阶段：

- 记录设备型号、Android 版本、ABI、root/Frida 版本、分辨率和导航模式。
- 固定应用初始状态、账号、权限、locale、网络响应和广告策略。
- 保存每轮候选路径、PHIL 调用、动作序列、runtime monitor 与执行时间。
- 至少重复三轮，分开报告确定性路径与 PHIL 路径。

性能扩展：

- Android 17 测试写明 API 37 与具体 build fingerprint。
- trace 在自动交互前启动，避免丢失入口和首帧。
- reachability 结果与性能指标使用不同字段。
- hook、重打包和 release 原包分别建基线。
- 结论同时给出目标 marker、线程/帧证据和无探针复测。

## 参考资料

- GAPS 论文 v3：[GAPS: Targeted Execution of Android Apps via Static Path Reconstruction](https://arxiv.org/abs/2511.23213v3)
- GAPS 公开复现快照：[GAPS README](https://anonymous.4open.science/r/GAPS/README.md)
- 动态交互库：[AndroidViewClient](https://github.com/dtmilano/AndroidViewClient)
- 动态插桩：[Frida](https://frida.re/)
- 资源反编译：[Apktool](https://apktool.org/)
- DEX 静态分析：[Androguard](https://github.com/androguard/androguard)
- 方法日志插桩：[AndroLog](https://arxiv.org/abs/2404.11223)
- Android trace API：[`android.os.Trace`](https://developer.android.com/reference/android/os/Trace)
- Perfetto Android tracing：[Android tracing quickstart](https://perfetto.dev/docs/quickstart/android-tracing)
