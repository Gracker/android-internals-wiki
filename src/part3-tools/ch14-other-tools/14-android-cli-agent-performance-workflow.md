---
title: "Android CLI 与 Agent 化性能调试工作流"
chapter: "14.14"
section: "14.14"
status: finalized
applicable_versions: "Android 17 (API 37)；Android CLI 1.0+；Android Studio Quail 2 Canary 1+（studio 命令预览能力）"
last_verified: "2026-08-13"
last_verified_against: "Android CLI 文档更新至 2026-06-16；Journeys 更新至 2026-07-17；Android skills 仓库相关 skill 更新至 2026-08-06；APA 更新至 2026-08-12；Macrobenchmark 更新至 2026-08-09；Android 17 SDK 更新至 2026-08-07；android-17.0.0_r1 / android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/tools/agents/android-cli"
  - type: official
    path: "https://developer.android.com/tools/agents/android-cli/journeys"
  - type: official
    path: "https://developer.android.com/tools/agents/android-skills"
  - type: official
    path: "https://developer.android.com/android-performance-analyzer"
  - type: official
    path: "https://developer.android.com/studio/profile"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/about/versions/17/setup-sdk"
  - type: official
    path: "https://perfetto.dev/docs/"
  - type: aosp
    path: "https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/trace_config.proto"
  - type: kernel
    path: "https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/05/android-cli-stable-1-0-agent-development.html"
  - type: blog
    path: "https://android-developers.googleblog.com/2026/05/whats-new-android-developer-tools.html"
  - type: blog
    path: "intake/daily-info/2026-05-21.md"
tags: [android-cli, agent, performance-tooling, android-studio, perfetto]
related_chapters: ["13.9", "13.12", "14.1", "14.17", "19.11"]
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
---

# 14.14 Android CLI 与 Agent 化性能调试工作流

Android CLI 1.0 把 Android 项目的环境准备、设备管理、应用运行、UI 状态读取和 IDE 语义查询放进同一个 `android` 命令入口。本文所说的 agent，是能规划步骤并调用命令或其他工具的 AI 执行程序；CLI 是 command-line interface，即命令行界面；IDE 是 integrated development environment，即集成开发环境。agent 可以用 CLI 准备实验并重放操作路径，再由 Profiler、Perfetto、APA（Android Performance Analyzer）或 Macrobenchmark 采集和计算性能数据。

## Android CLI 在性能工具链里的位置

Android CLI 负责把项目、SDK、设备、APK、UI 状态和 IDE 查询接到同一套命令流程中。它不生成帧级测量数据，也不能代替系统追踪分析。

| 工具 | 主要回答的问题 | 性能工作里的输出 | 边界 |
|---|---|---|---|
| Android CLI | agent 如何读取项目、SDK、设备、APK、UI 状态和 IDE 符号信息 | JSON 项目描述、SDK/设备状态、截图、UI 布局树、IDE 查询结果 | 不计算性能指标，不替代 trace / profiler |
| Android Studio Profiler | App 进程内 CPU、内存、网络、功耗如何变化 | CPU / Memory / Power / System Trace 数据，详见 14.1 节 | IDE 交互强，批量回归和跨 trace 对比能力有限 |
| Android Performance Analyzer | CPU、GPU、内存、功耗、SurfaceFlinger 事件如何同时变化 | Perfetto Trace 项目、GPU counter、截图时间线，详见 14.17 节 | 侧重 trace 浏览与对比；复现条件仍需单独控制 |
| Perfetto UI / Trace Processor | Trace 里的线程、slice、counter、帧时间如何定量分析 | `.perfetto-trace`、SQL 查询、表格结果，详见 13.10 和 13.12 节 | 采集、场景复现和项目管理需要另行组织 |
| Macrobenchmark / Jetpack Benchmark | 同一场景在多次运行里的指标是否稳定 | 启动耗时、帧时间、Baseline Profile 验证结果 | 需要设计可重复场景和设备基线，详见 19.11 节 |

这里的 trace 是按时间记录系统与 App 事件的文件；slice 是带时间戳和持续时间的一段事件，counter 是随时间变化的数值轨道；Baseline Profile 则是帮助系统提前编译常用代码路径的规则。一次排查可以先用 CLI 固定复现状态，再用 Trace 或 Profiler 采集数据，随后通过 SQL、APA 或 Benchmark 得出可复查的结果。

## Android 17 源码基线与证据边界

Android CLI 是独立发布、运行在开发机或 CI 机器上的主机工具。它不属于 `android-17.0.0_r1` framework，也没有名为“Android CLI”的 API 37 SDK 接口。一次实验需要同时记录三组版本信息：

- Android CLI 版本：决定命令、参数、默认模板和 skill 安装行为；
- 设备 build fingerprint（构建的唯一标识字符串）与 Android 17 / API 37 平台版本：决定 framework、ART（Android Runtime）、SurfaceFlinger 合成器和 Perfetto 事件；
- 设备实际 kernel 与 vendor driver（厂商驱动）版本：决定 scheduler tracepoint（调度器事件记录点）、CPU/GPU 能力和设备特有数据。`android17-6.18-2026-06_r6` 只能作为 Android common kernel 的源码参照，真机可能包含厂商修改。

例如，APA 或 Perfetto 读取的录制配置，对应 Android 17 源码中的 `external/perfetto/protos/perfetto/config/trace_config.proto`。调度分析会使用 `include/trace/events/sched.h` 中的 `sched_switch`、`sched_wakeup` 等事件；分析真机 trace 时，还要以该设备内核实际提供的事件为准。CLI 可以启动 App、保存画面或触发测试，但不会改变这些事件的含义。

截图、布局树和 Journey 结果只能证明“agent 看到了什么、执行了什么”。帧耗时、CPU 调度、GPU 执行和功耗结论还要依据 trace、benchmark metric（基准测试指标）或硬件测量。官方 Macrobenchmark 文档不建议用模拟器产出的性能数字代表终端用户体验，并会把模拟器测量视为配置错误；模拟器更适合验证安装、页面路径和断言，发布级性能结论应在受控的物理设备上采集。

## 项目描述、SDK 与设备基线

性能复现实验应先固定环境。`android --version`、`describe`、`info`、`sdk` 和 `emulator` 命令适合在 agent 操作前生成基线记录。`android update` 更新 Android CLI 本身，`android sdk update` 更新 SDK package（SDK 软件包），两条命令用途不同。

| 命令 | 适合记录的基线 | 在性能流程里的用法 |
|---|---|---|
| `android --version` / `android update` | CLI 版本 | 保存实际运行版本；升级后先重读帮助并执行最小可运行检查 |
| `android init` | `android-cli` skill 安装状态 | 为已识别的 agent 安装基础 skill；不配置 SDK 或设备 |
| `android describe [--project_dir=...]` | 项目结构、build target、构建输出的 JSON 路径、APK 位置 | 让 agent 从结构化结果里找到 APK，无需猜测 Gradle 输出目录 |
| `android info` | 当前默认 Android SDK 路径 | 记录本轮测试使用的 SDK，避免多 SDK 环境使用不同版本 |
| `android --sdk=<path> ...` | 单次命令使用的 SDK | 在 CI 或多项目机器上显式绑定 SDK |
| `android sdk list/install/update` | 平台包、build-tools、system image 版本 | 建立 Android 平台、工具链和模拟器镜像版本基线 |
| `android emulator create/list/start/stop` | 虚拟设备 profile、设备名、serial | 先创建 AVD，再启动列表中的设备；Windows 侧 `android emulator` 命令当前被官方禁用 |
| `android docs search/fetch` | Android Knowledge Base（官方知识库）查询及返回内容 | 为 agent 提供官方文档上下文；不能替代项目源码与设备 trace |

`android describe` 会输出一个 JSON（结构化文本格式）文件路径，该文件描述项目结构、build target（构建目标）和 artifact（构建输出）位置。命令本身不执行 Gradle 构建；调用前仍要明确 build variant（构建变体，如 `debug`、`benchmark` 或 `release`），并确认 APK 的时间戳、校验值和代码提交。agent 因而无需从 `app/build/outputs/` 猜文件，也无需把临时路径写死在提示词里。

SDK 和设备基线至少要记录 Android SDK 路径、`platforms/android-37` package revision（软件包修订号）、build-tools / platform-tools 版本，以及设备 serial 或 emulator profile。serial 是 adb 用来区分设备的标识，emulator profile 是虚拟设备配置。涉及帧率、启动耗时、功耗和 GPU counter 的测试，还要保存设备型号、build fingerprint、刷新率、电池与温度状态及 GPU driver；这些内容需要测试脚本或人工补齐。

`android emulator create --profile=medium_phone` 用于创建 AVD（Android Virtual Device，Android 虚拟设备），`android emulator start medium_phone` 只能启动已经存在且名称匹配的设备。旧 CI 模板直接调用 `start`，在全新 runner（执行 CI 任务的机器）上会失败。AVD provisioning，即虚拟设备的预先创建与配置，应在任务开始前完成；也可以先用 `emulator list` 检查，再按需创建。缺少 API 37 platform 或目标 system image（系统镜像）时，先通过 `sdk list/install` 安装。

`.androidrc` 可以把常用全局参数保存在用户目录，例如默认 `--sdk=<path-to-sdk>`。这种配置适合个人机器；团队 CI 的必要配置应直接写入任务脚本。显式传入 `--sdk` 后，构建日志也能显示本次使用的环境。

## `run`、`layout`、`screen` 在复现流程中的边界

`android run` 只负责把给定 APK 安装到设备并启动组件。官方文档明确说明，该命令不执行构建步骤，调用方必须传入 APK 路径；多 APK 安装可以通过逗号分隔的 `--apks` 完成。构建与运行分别记录后，测试报告才能说明本次使用的是哪一个 APK。

下面的命令演示安装单 APK、指定设备和显式启动 Activity；它们都假设 APK 已经构建完成。

```bash
# 安装并启动默认设备上的 APK；APK 路径通常来自 android describe 或 CI 产物
android run --apks=app/build/outputs/apk/debug/app-debug.apk

# 多设备并行测试时显式指定设备 serial
android run --apks=app-debug.apk --device=emulator-5554

# 明确指定要启动的 Activity
android run --apks=app-debug.apk --type=ACTIVITY --activity=.MainActivity
```

前三条命令分别覆盖默认设备、指定 serial 和指定 Activity 三种启动方式。发布级性能测试应使用接近 `release` 优化配置、同时满足 non-debuggable（不可调试）与 profileable（允许 shell 进行低开销性能采样）的构建。`--debug` 适合断点和诊断，相关结果不应与发布构建的基线数字放在同一组。官方页面当前还有一处矛盾：示例使用 `--type=SERVICE`，支持类型列表却没有列出 `SERVICE`。涉及后台组件时，应以所用 CLI 版本的 `android run --help` 和实机试运行为准，不把这个示例视为稳定接口。

`android layout` 返回当前活动 App 的 UI 布局树 JSON，也就是按层级组织的界面节点数据。`--diff` 只输出相对命令内部上一次快照发生变化的节点。它适合确认 agent 是否进入了正确页面、某个按钮是否出现，以及操作前后哪些节点改变。布局树不能解释帧耗时，也不具备 Layout Inspector 的完整交互能力；分析 measure / layout / draw 成本仍需使用 Perfetto、Profiler 或相关章节介绍的 View 绘制流程。

`android screen capture` 负责截屏，`--annotate` 会给识别到的 UI 元素绘制编号框。`android screen resolve --screenshot=ui.png --string="input tap #5"` 会把截图上的编号替换为实际坐标；命令只返回替换后的字符串，调用方还要执行相应的输入命令。这组能力可以留存当时的屏幕状态，并说明点击坐标如何得到。它无法解释某一帧卡顿的原因，也不能替代 FrameTimeline（逐帧预期与实际时间轨道）、SurfaceFlinger 合成记录或 GPU counter（随时间采样的 GPU 数值）。

当前 `layout` 与 `screen capture` 文档没有列出 `--device` 参数。多设备 CI runner 应隔离 adb（Android Debug Bridge）server，或保证任务期间只向 CLI 暴露目标设备，并在截图、布局树和 trace 文件名中记录 serial。仅在 `android run` 中指定 `--device`，无法确认后续 UI 命令仍指向同一台设备。

在性能复现中，可以依次安装目标 APK、进入目标页面、截屏确认状态、导出布局树并执行交互，最后把 trace 或 benchmark 输出放进同一份报告。这样会得到一组可复查的输入与结果：APK、设备、页面状态、操作坐标、trace 文件和指标数据。

## Journeys 与关键用户路径回归

Journeys 用自然语言描述用户在 App 中要完成的路径。agent 会把指令转换为界面交互，再依据设备画面判断断言是否成立。断言是对预期结果的可检查描述，例如“详情页标题已经出现”。官方页面在 2026 年 7 月 17 日更新后，仍由 agent 和 CLI 附带的 skills 创建、运行 Journey，并明确提到可接入 CI/CD（持续集成与持续交付）。

性能场景里的 Journey 不应只写“打开首页并滑动列表”。一条可复现的用户路径至少要补齐这些条件：

- 入口状态：冷启动、温启动、后台恢复、登录态、缓存是否清空。
- 页面路径：启动页、首页、列表页、详情页、返回路径，每一步都要有可观察 UI 标记。
- 交互动作：点击、输入、滚动、等待网络、横竖屏切换、返回键。
- 断言条件：目标页面出现、错误提示不出现、列表加载完成、关键按钮可点击。
- 性能采集窗口：明确从哪个动作前开始 trace、在哪个 UI 标记出现后停止，也就是界定纳入统计的时间范围。
- 失败处理：页面未出现、登录失效、网络超时、权限弹窗干扰时如何退出并保存截图。

Journey 适合准备登录态、导航到目标页面、确认异常是否出现，并记录失败画面。自然语言理解、视觉识别、坐标选择和 agent 模型都会带来执行差异，因此不适合控制 benchmark 的计时区间。测量窗口内的启动、滚动和动画应交给 Macrobenchmark 与 UI Automator；UI Automator 是 Android 的跨 App 界面自动化框架。指标应来自 Macrobenchmark、Perfetto Trace、APA 或线上 APM（Application Performance Monitoring，应用性能监控）。冷启动耗时、帧时间分布、CPU 调度、GPU counter、GC（garbage collection，垃圾回收）暂停和 Binder（Android 进程间通信机制）等待时间，都不能从 Journey 的成功或失败直接推导。

官方 Journey 页面没有发布固定的 `android journey ...` 子命令格式，因此本文不编造这类命令。文件格式、运行步骤和 CI 接入方式应以当前 Android CLI、Journeys skill 及项目实际生成的文件为准。报告还要记录 CLI、agent、模型、skill 版本或内容快照，避免直接比较不同执行环境得出的结果。

## Android Studio 语义命令与性能排查协作

`android studio` 命令仍处于 Preview（预览）状态，接口可能调整。官方文档给出的前提是：项目已在 Android Studio Quail 2 Canary 1 或更高版本中打开，并且 Gemini in Android Studio 已启用、已登录。Canary 是更新快、稳定性低于 Beta 和 Stable 的预览渠道。满足条件后，agent 可以通过 CLI 连接正在运行的 Android Studio 实例，执行理解代码符号与项目结构的查询；这类查询比纯文本搜索多了声明、引用和类型信息。

| 命令 | 输出 | 性能排查里的用法 |
|---|---|---|
| `android studio check` | Android Studio PID、版本、打开的项目状态 | 多 IDE 实例时选择目标项目，确认 CLI 与 IDE 已连接；PID 是进程编号 |
| `android studio analyze-file <path>` | Kotlin / Java 文件里的错误、警告、lint | 修改性能相关代码后执行 IDE 静态检查；lint 是一组静态规则检查 |
| `android studio find-declaration <symbol>` | 符号声明位置，可用 `--context-file` 消歧 | 从 trace 里的类名、方法名跳到源码定义 |
| `android studio find-usages <symbol>` | 符号引用位置 | 判断某个性能入口是否还有其他调用方 |
| `android studio open-file <path>` | 在 Android Studio 当前编辑器打开文件 | 把 agent 找到的源码、trace、报告交给人工复核 |
| `android studio render-compose-preview <path> <composable>` | Compose Preview PNG，可选语义树 JSON | 改 Compose UI 后确认画面和供无障碍、测试使用的语义节点 |
| `android studio version-lookup <artifacts...>` | Maven、AGP（Android Gradle Plugin）、Gradle、NDK（Native Development Kit）、SDK、Compose、Kotlin 等版本信息 | 核对工具链和依赖版本，减少手工查版本带来的误差 |

这组命令适合源码定位和人工复核。例如，trace 显示某段 Compose 页面在滑动时发生大量重组，即 Compose 多次重新执行相关 UI 代码。agent 可以先用 `find-declaration` 找到相关函数，再用 `analyze-file` 检查修改后的文件，并通过 `render-compose-preview --print-semantics` 为目标预览函数生成预览图和语义树。这里的预览函数必须带 `@Preview`，通常也会带 `@Composable`。若 release trace 中的符号已混淆或只剩地址，还需要 mapping（混淆前后名称映射）、native symbol（本地代码地址与函数名的映射）或对应的源码版本协助定位。帧时间是否改善仍要由 trace 或 benchmark 验证。

`version-lookup` 返回仓库或工具渠道中的可用新版本，但不会判断版本是否适合当前项目，也不会替团队选择 Stable、Beta 或 Canary。三者大致对应稳定发布、较成熟预览和早期预览；升级时仍要检查版本目录、依赖锁、AGP/Gradle 兼容表和回归测试。

## Android skills 与性能专项能力

Android skills 是供 AI 工具和 agent 使用的指令包。每个 skill 通常以 `SKILL.md` 说明适用任务和执行步骤，还可以附带脚本、模板与参考资料。官方文档列出的能力包括 XML 到 Compose 迁移、AGP 9 升级、Navigation 3、edge-to-edge UI（内容延伸到系统栏区域）和 R8 配置检查。R8 是 Android 构建中的代码压缩与优化工具。skill 为 agent 提供特定 Android 任务的操作方法，其输出仍需验证。

`android init` 是最短的初始化入口，用来安装基础 `android-cli` skill。Android CLI 还提供 `skills list/find/add/remove` 管理能力：

- `android skills list --long`：列出可用 skill、描述和已安装到哪些 agent。
- `android skills find 'performance'`：按描述搜索与性能相关的 skill。
- `android skills add --skill=<skill-name>`：安装或更新单个 skill；省略 `--skill` 和 `--all` 时默认安装 `android-cli` skill。官方仓库示例还用 `--project=.` 指定当前项目根目录。
- `android skills add --all`：一次安装或更新全部 Android skills。
- `android skills remove --skill=<skill-name>`：从一个或多个 agent 目录移除 skill。

更新规则要写进团队规范。官方文档提醒，如果修改了已安装的 skill，应换一个名称保存，否则后续执行 `skills add` 时可能被最新版覆盖。项目自定义 skill 放在仓库根目录的 `.skills/` 或 `.agent/skills/` 下，每个 skill 目录都要包含大小写固定的 `SKILL.md`。团队把 Perfetto SQL 模板、R8 检查流程或启动回归脚本写入自定义 skill 时，应使用内部名称，并记录来源和版本。

当前官方仓库中，与性能工作较相关的目录包括四个：`profilers/perfetto-sql` 把自然语言问题转换成有效的 Perfetto SQL，并对本地 trace 执行；`profilers/perfetto-trace-analysis` 调查延迟、内存或卡顿的原因；`testing/testing-setup` 分析并建立原生 Android 测试策略与测试基础设施；`performance/r8-analyzer` 检查构建文件和 R8 keep rules（指定哪些类或成员必须保留的规则），找出重复或范围过大的规则。这些名称是仓库目录和 skill 名称，不是 `android` 子命令。

安装或升级后，应先检查 `SKILL.md`、附带脚本和资源，再允许 agent 执行。当前 CLI 文档只描述“更新到最新版”，没有提供固定 skill 版本的参数。需要重复同一实验时，应在记录中保存已审核内容对应的提交或归档。skill 得出的结论还要复核 trace 表结构、字段单位、编译模式和设备条件。

## 与 APA / Perfetto / Macrobenchmark 的分工

把 Android CLI 加入现有工具后，可以按“环境 → 复现 → 采集 → 分析 → 回归”的顺序组织材料：

| 阶段 | Android CLI 做什么 | 其他工具做什么 | 输出 |
|---|---|---|---|
| 环境 | `android info`、`android sdk list`、`android emulator list/start` 记录 SDK 和设备 | CI 记录构建号、git commit、设备温度、电量、刷新率 | 环境基线 |
| 复现 | `android run` 安装 APK，Journey 或 screen/layout 驱动页面 | 人工确认测试账号、弱网、权限弹窗等条件 | 页面状态、截图、布局树 |
| 采集 | CLI 触发前置动作和结束动作 | Profiler / Perfetto / APA / Macrobenchmark 采集 trace 或指标 | trace、profile、benchmark JSON |
| 分析 | `android studio find-declaration/find-usages/open-file` 关联源码 | Perfetto SQL、APA、Profiler 做证据分析 | SQL、截图、源码定位 |
| 回归 | agent 准备同一入口状态；计时窗口外可用 Journey | Macrobenchmark 或 CI 阈值检查对比指标 | 趋势表、阈值判断、失败截图 |

Android CLI 负责准备环境、运行 App 和定位源码。14.17 节的 APA 在同一时间窗口分析 CPU、GPU、内存、功耗与 SurfaceFlinger；13.9 节的 Perfetto SQL 从 trace 表中计算定量结果；19.11 节的 Macrobenchmark 重复执行受控场景并输出指标。设备基线、APK、操作脚本、trace 和查询共同标识一次实验，让各工具的结果可以相互核对。

## CI 与本地 agent 工作流模板

一条最小可复现流程包含六类材料：环境记录、项目描述、设备状态、Journey 或操作脚本、trace / benchmark 输出和分析报告。下面的脚本骨架补上了 AVD 预先创建与启动完成检查。脚本中的 `release-like/profileable` 指接近 release 优化配置、同时允许低开销 profiling 的测量构建。由于 `layout` 和 `screen capture` 没有公开 `--device` 参数，示例还假设任务期间只有目标设备对 Android CLI 可见。真实性能数字仍应在固定的物理设备上采集。

```bash
set -euo pipefail

PROJECT_ROOT="$PWD"
PERF_OUT_DIR="$PROJECT_ROOT/out/perf-run-$(date +%Y%m%d-%H%M%S)"
TEST_DEVICE_NAME="${TEST_DEVICE_NAME:?set TEST_DEVICE_NAME to an existing AVD name}"
TEST_DEVICE_SERIAL="${TEST_DEVICE_SERIAL:?set TEST_DEVICE_SERIAL after device allocation}"
mkdir -p "$PERF_OUT_DIR"

# 1. 记录 CLI、SDK 和项目结构
android --version > "$PERF_OUT_DIR/android-version.txt"
android info > "$PERF_OUT_DIR/android-info.txt"
android sdk list 'platforms/android-37|build-tools|platform-tools|emulator' \
  > "$PERF_OUT_DIR/android-sdk-list.txt"
android describe --project_dir="$PROJECT_ROOT" \
  > "$PERF_OUT_DIR/android-describe.txt"

# 2. AVD 只在 provisioning 阶段创建：
# android emulator create --profile=medium_phone
android emulator list > "$PERF_OUT_DIR/emulator-list.txt"
android emulator start "$TEST_DEVICE_NAME" \
  > "$PERF_OUT_DIR/emulator.log" 2>&1 &
adb -s "$TEST_DEVICE_SERIAL" wait-for-device
until [[ "$(adb -s "$TEST_DEVICE_SERIAL" shell getprop sys.boot_completed \
  | tr -d '\r')" == "1" ]]; do
  sleep 2
done

# 3. 保存设备平台身份
adb -s "$TEST_DEVICE_SERIAL" shell getprop ro.build.fingerprint \
  > "$PERF_OUT_DIR/build-fingerprint.txt"
adb -s "$TEST_DEVICE_SERIAL" shell getprop ro.build.version.sdk \
  > "$PERF_OUT_DIR/api-level.txt"

# 4. 安装并启动已构建的 release-like/profileable APK
android run \
  --apks="$PROJECT_ROOT/app/build/outputs/apk/benchmark/app-benchmark.apk" \
  --device="$TEST_DEVICE_SERIAL"

# 5. 保存测量前的页面状态
android screen capture --output="$PERF_OUT_DIR/before.png" --annotate
android layout --pretty --output="$PERF_OUT_DIR/layout-before.json"

# 6. 计时区间由 Macrobenchmark / UI Automator 驱动；
# Journey 可用于区间外的前置导航和失败诊断。

# 7. 保存测量后的 UI 状态；trace / benchmark 由相应工具输出
android screen capture --output="$PERF_OUT_DIR/after.png" --annotate
android layout --pretty --output="$PERF_OUT_DIR/layout-after.json"
```

`emulator start` 在后台运行，所以脚本会等待 adb 连接和 `sys.boot_completed=1`。这个属性只说明系统完成启动，无法说明温度、编译状态、网络和后台任务已经满足测量条件。启动回归可以使用 Macrobenchmark；卡顿排查可以使用 Perfetto 或 APA；功耗分析还要采集电源、温度和电池数据；Compose UI 变更可以通过 `android studio render-compose-preview` 检查预览结果。

## 隐私与 Telemetry（遥测）边界

Telemetry 是工具为了解使用情况和故障而发送的数据。Android CLI 官方文档写明会收集 `android` 命令与子命令、选项名称、固定枚举型系统选项值，以及经过匿名化处理的堆栈和异常消息。文档同时说明，它不收集命令响应，也不收集用户创建的位置参数或外部标识符的值，例如 Maven 坐标（依赖的 group、artifact 与 version 标识）、文件路径和自定义项目名。

企业内网使用时，报告里应单独记录三类内容：

- 命令日志：是否包含本地路径、包名、账号、设备 serial、截图或布局树里的业务数据。
- agent 上下文：是否把 trace、截图、布局树或源码片段交给外部模型。
- skill 来源：官方 skill、团队内部 skill、第三方 skill 分开管理，更新记录要可追溯。

`screen capture` 和 `layout` 会直接读取设备画面与 UI 树，因而比 `android info` 或 `sdk list` 更容易包含业务数据。Perfetto SQL skill 还可能读取本地 trace，Journey agent 会接收自然语言步骤和设备画面。涉及用户数据、测试账号、订单页、聊天页或健康数据时，应使用隔离测试环境，并在报告发布前删除或遮盖可识别个人与业务的信息。

## 小结

Android CLI 为 agent 提供项目描述、SDK 与设备管理、UI 状态读取和 IDE 符号查询入口。它能补全复现输入，但截图、布局树和 Journey 成功都不能单独支持性能结论。Android 17 上的结果应绑定 CLI 版本、设备 build fingerprint、实际 kernel 与 vendor driver；`android-17.0.0_r1` 和 `android17-6.18-2026-06_r6` 可作为对应源码的参照。最后还要由 Profiler、Perfetto、APA、Macrobenchmark 或线上指标验证。

## 参考资料

- [Android CLI](https://developer.android.com/tools/agents/android-cli)
- [Android CLI support for Journeys](https://developer.android.com/tools/agents/android-cli/journeys)
- [Android skills](https://developer.android.com/tools/agents/android-skills)
- [Android CLI 1.0 announcement](https://android-developers.googleblog.com/2026/05/android-cli-stable-1-0-agent-development.html)
- [Android Performance Analyzer](https://developer.android.com/android-performance-analyzer)
- [Android Studio performance profilers](https://developer.android.com/studio/profile)
- [Write a Macrobenchmark](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Set up the Android 17 SDK](https://developer.android.com/about/versions/17/setup-sdk)
- [Perfetto documentation](https://perfetto.dev/docs/)
- [Android 17 Perfetto `TraceConfig`](https://android.googlesource.com/platform/external/perfetto/+/refs/tags/android-17.0.0_r1/protos/perfetto/config/trace_config.proto)
- [Android 17 common kernel scheduler tracepoints](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/sched.h)
