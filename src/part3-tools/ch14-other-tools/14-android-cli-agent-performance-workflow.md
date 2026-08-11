---
title: "Android CLI 与 Agent 化性能调试工作流"
chapter: "14.14"
section: "14.14"
status: finalized
drafted_date: "2026-05-22"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 17 (API 37)；Android CLI 1.0+；Android Studio Quail 2 Canary 1+（studio 命令预览能力）"
last_verified: "2026-07-30"
last_verified_against: "Android CLI 文档更新至 2026-06-16；Journeys 更新至 2026-07-17；Macrobenchmark 更新至 2026-07-14；android-17.0.0_r1 / android17-6.18-2026-06_r6"
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
created_by: "task2a-knowledge-gap"
created_date: "2026-05-22"
gap_source: "官方文档/每日信息/研究素材"
pipeline_stage: ready-to-publish
task6_state: reviewed
last_task2a_at: "2026-05-22T03:16:00+08:00"
reviewed_by: openclaw-task6
reviewed_date: "2026-05-22"
task6_result: pass-light-edit
task9_state: reviewed
last_task6_at: "2026-05-22T04:07:00+08:00"
last_task6_audit: "2026-07-07"
last_task6_review_log: "logs/review/2026-05-22-04-review.md"
task6_review_notes: "2026-05-22 task6 review：pass-light-edit。小修 1 处（补 section 元数据）。无 B 类大问题；Task9 尚未通过，未自动晋升。"
task9_result: pass-tech-review
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-22"
last_task9_at: "2026-05-22T04:51:16+08:00"
task9_review_notes: "2026-05-22 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 1（CI 模板需补 AVD create 前置条件，已写入 suggestions）。Task6 已通过且 queue 无 pending，自动晋升 finalized。"
last_task9_review_log: "logs/deep-review/2026-07-17-08-idle-audit.md"
last_task9_audit: "2026-07-17"
last_idle_task9_at: "2026-07-17T18:00:00+08:00"
deepseek_polish_state: done
last_deepseek_polish_at: "2026-05-24"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-24
android17_review_notes: "2026-07-30：按 Android CLI、Journeys、Android skills 与 Macrobenchmark 当前官方文档复核命令和边界；补充 android update 与 sdk update 的区别、AVD 创建前置条件、run --type 文档矛盾、Journey 非确定性、模拟器指标限制，以及 Android 17 / API 37 / android-17.0.0_r1 与 android17-6.18-2026-06_r6 的证据锚点。原 task6/task9/OpenClaw 字段保留。"
---

# 14.14 Android CLI 与 Agent 化性能调试工作流

Android CLI 1.0 把 Android 项目的环境准备、设备管理、应用运行、UI 状态读取和 IDE 语义能力放进同一个 `android` 命令入口。它适合放在 agent 工作流的控制层：agent 用 CLI 准备实验并重放路径，Profiler、Perfetto、APA 或 Macrobenchmark 负责采集和计算性能证据。

## Android CLI 在性能工具链里的位置

Android CLI 的定位是命令入口和工作流胶水。它不生成帧级证据，也不替代系统追踪分析；它负责让 agent 知道项目在哪里、APK 在哪里、设备是什么、当前 UI 是什么状态、源码符号该跳到哪里。

| 工具 | 主要回答的问题 | 性能工作里的产物 | 边界 |
|---|---|---|---|
| Android CLI | 项目、SDK、设备、APK、UI 状态、IDE 语义能力如何被 agent 调用 | JSON 项目描述、SDK/设备状态、截图、布局树、IDE 查询结果 | 不负责构建性能指标，不替代 trace / profiler |
| Android Studio Profiler | App 进程内 CPU、内存、网络、功耗如何变化 | CPU / Memory / Power / System Trace 数据，详见 14.1 节 | IDE 交互强，批量回归和跨 trace 对比能力有限 |
| Android Performance Analyzer | CPU、GPU、内存、功耗、SurfaceFlinger 事件如何同时变化 | Perfetto Trace 项目、GPU counter、截图时间线，详见 14.17 节 | Beta 阶段；结论仍要回到 trace 数据复核 |
| Perfetto UI / Trace Processor | Trace 里的线程、slice、counter、帧时间如何定量分析 | `.perfetto-trace`、SQL 查询、表格结果，详见 13.10 和 13.12 节 | 采集、场景复现和项目管理需要另行组织 |
| Macrobenchmark / Jetpack Benchmark | 同一场景在多次运行里的指标是否稳定 | 启动耗时、帧时间、Baseline Profile 验证结果 | 需要设计可重复场景和设备基线，详见 19.11 节 |

这张表决定了 Android CLI 的用法：它是 agent 的控制台，性能结论交给 Trace、Profiler、SQL、APA 或 Benchmark。一轮排障可以从 CLI 建立复现状态开始，再用 Trace / Profiler 采集证据，后续用 SQL、APA 或 Benchmark 把结论整理成可复查记录。

## Android 17 平台锚点与证据边界

Android CLI 是独立发布的主机工具，不属于 `android-17.0.0_r1` framework，也没有名为“Android CLI”的 API 37 SDK 接口。一次实验需要同时记录三个版本：

- Android CLI 版本：决定命令、参数、默认模板和 skill 安装行为；
- 设备 build fingerprint 与 Android 17 / API 37 平台版本：决定 framework、ART、SurfaceFlinger 和 Perfetto 事件；
- kernel `android17-6.18-2026-06_r6` 及 vendor driver：决定 scheduler tracepoint、CPU/GPU 能力和设备特有数据。

例如，APA 或 Perfetto 读取的录制配置对应 Android 17 源码中的 `external/perfetto/protos/perfetto/config/trace_config.proto`；调度分析依赖固定内核锚点 `include/trace/events/sched.h` 中的 `sched_switch`、`sched_wakeup` 等事件。CLI 可以启动 App、保存画面或触发测试，但不会改变这些事件的含义。

截图、布局树和 Journey 结果只能证明“agent 看到了什么、执行了什么”。帧耗时、CPU 调度、GPU 执行和功耗结论还要回到 trace、benchmark metric 或硬件测量。官方 Macrobenchmark 文档也不建议用模拟器产出的性能数字代表终端用户体验；模拟器适合验证安装、页面路径和断言，物理设备用于发布级性能结论。

## 项目描述、SDK 与设备基线

性能复现实验先固定环境。`android --version`、`describe`、`info`、`sdk` 和 `emulator` 命令适合在 agent 开始操作前生成基线记录。`android update` 更新 Android CLI 本身，`android sdk update` 更新 SDK package，两者不能混用。

| 命令 | 适合记录的基线 | 在性能流程里的用法 |
|---|---|---|
| `android --version` / `android update` | CLI 版本 | 保存实际运行版本；升级后先重跑帮助和冒烟测试 |
| `android init` | `android-cli` skill 安装状态 | 为已识别的 agent 安装基础 skill；不配置 SDK 或设备 |
| `android describe [--project_dir=...]` | 项目结构、build target、输出产物 JSON 路径、APK 位置 | 让 agent 从结构化结果里找到 APK，不靠猜 Gradle 输出目录 |
| `android info` | 当前默认 Android SDK 路径 | 记录本轮测试使用的 SDK，避免多 SDK 环境下口径漂移 |
| `android --sdk=<path> ...` | 单次命令使用的 SDK | 在 CI 或多项目机器上显式绑定 SDK |
| `android sdk list/install/update` | 平台包、build-tools、system image 版本 | 建立 Android 平台、工具链和模拟器镜像版本基线 |
| `android emulator create/list/start/stop` | 虚拟设备 profile、设备名、serial | 先创建 AVD，再启动列表中的设备；Windows 侧 `android emulator` 命令当前被官方禁用 |
| `android docs search/fetch` | Android Knowledge Base 查询及返回内容 | 为 agent 提供官方文档上下文；不能替代项目源码与设备 trace |

`android describe` 会输出描述项目结构、build target 和 artifact 位置的 JSON 文件路径。它不执行 Gradle 构建；调用前仍要明确构建 variant，并确认 APK 的时间戳、校验值和代码提交。agent 无需从 `app/build/outputs/` 猜文件，也无需把构建系统的临时路径写死到提示词里。

SDK 和设备基线至少记录 Android SDK 路径、`platforms/android-37` package revision、build-tools / platform-tools 版本、设备 serial 或 emulator profile。涉及帧率、启动耗时、功耗和 GPU counter 的测试，还要保存设备型号、build fingerprint、刷新率、电池/温度状态和 GPU driver；这些内容需要测试脚本或人工补齐。

`android emulator create --profile=medium_phone` 是创建动作，`android emulator start medium_phone` 只能启动已经存在且名称匹配的虚拟设备。旧 CI 模板直接调用 `start`，在全新 runner 上会失败。AVD provisioning 应在任务前完成，或在脚本中先用 `emulator list` 检查并创建；缺少 API 37 platform 或目标 system image 时，先通过 `sdk list/install` 补齐。

`.androidrc` 可以把常用全局参数固化到用户目录，例如默认 `--sdk=<path-to-sdk>`。这适合个人机器，不适合把团队 CI 的关键配置只放在用户目录；CI 脚本应显式传入 `--sdk`，让构建日志自己带上环境口径。

## `run`、`layout`、`screen` 在复现流程中的边界

`android run` 只负责把给定 APK 安装到设备并启动组件。官方文档明确写到，它不执行构建步骤，调用方必须传入 APK 路径；多 APK 安装可以通过逗号分隔的 `--apks` 完成——构建和运行分开，测试报告里能清楚区分“这次测的是哪个构建产物”。

下面的命令演示安装单 APK、指定设备和显式启动 Activity；它们都假设 APK 已经构建完成。

```bash
# 安装并启动默认设备上的 APK；APK 路径通常来自 android describe 或 CI 产物
android run --apks=app/build/outputs/apk/debug/app-debug.apk

# 多设备并行测试时显式指定设备 serial
android run --apks=app-debug.apk --device=emulator-5554

# 明确指定要启动的 Activity
android run --apks=app-debug.apk --type=ACTIVITY --activity=.MainActivity
```

`--debug` 会以调试方式部署，之后还要由 IDE 或命令行调试器连接。发布级性能测试应使用接近 release 的 non-debuggable/profileable 构建；`--debug` 留给断点和诊断，不应与基线数字混在同一组。官方页面当前还存在一处文档矛盾：示例使用 `--type=SERVICE`，支持类型列表却没有列出 `SERVICE`。涉及后台组件时，先以当前版本的 `android run --help` 和实机试运行为准，不把该示例当作稳定接口。

`android layout` 返回当前活动 App 的 UI 布局树 JSON，`--diff` 只输出自上次内部快照以来变化的节点。它适合确认 agent 是否进入了正确页面、某个按钮是否出现、一次操作前后布局状态是否变化。布局树不能解释帧耗时，也不能替代 Layout Inspector 的完整交互能力；要分析 measure / layout / draw 成本，仍要回到 Perfetto、Profiler 或相关章节里的 View 管线分析方法。

`android screen capture` 负责截屏，`--annotate` 会给识别到的 UI 元素绘制编号框。`android screen resolve --screenshot=ui.png --string="input tap #5"` 把截图上的编号替换为实际坐标；命令只返回替换后的字符串，调用方还要显式执行对应输入命令。这组能力适合让 agent 留存截图并解析点击位置，证据口径是“当时屏幕上是什么”和“坐标如何解析”。它不能证明某一帧为什么卡，也不能替代 FrameTimeline、SurfaceFlinger 或 GPU counter。

当前 `layout` 与 `screen capture` 文档没有列出 `--device` 参数。多设备 CI runner 应隔离 adb server 或保证任务期间只暴露目标设备，并在截图、布局树和 trace 文件名中记录 serial；仅在 `android run` 中指定 `--device`，不能证明后续 UI 命令仍指向同一设备。

在性能复现里，`run / layout / screen` 的合理顺序是：安装目标 APK，进入目标页面，截屏确认状态，导出布局树，执行交互，再把 trace 或 benchmark 产物挂到同一份报告里。这样保存下来的材料是一组可复查输入：APK、设备、页面状态、操作坐标、trace 文件和指标结果。

## Journeys 与关键用户路径回归

Journeys 是 Android CLI 面向 agent 的用户路径描述能力。Journey 由自然语言指令组成，agent 把指令转换为 App 交互，并依据设备画面判断断言。官方页面在 2026 年 7 月 17 日更新后仍把创建和运行交给 agent 与随 CLI 提供的 skills，也明确提到可以接入 CI/CD。

性能场景里的 Journey 不应只写“打开首页并滑动列表”。一条可复现的用户路径至少要补齐这些条件：

- 入口状态：冷启动、温启动、后台恢复、登录态、缓存是否清空。
- 页面路径：启动页、首页、列表页、详情页、返回路径，每一步都要有可观察 UI 标记。
- 交互动作：点击、输入、滚动、等待网络、横竖屏切换、返回键。
- 断言条件：目标页面出现、错误提示不出现、列表加载完成、关键按钮可点击。
- 性能采集窗口：从哪个动作前开始 trace，从哪个 UI 标记后结束采集。
- 失败处理：页面未出现、登录失效、网络超时、权限弹窗干扰时如何退出并保存截图。

Journey 适合准备登录态、导航到目标页面、确认异常是否出现，并记录失败画面。自然语言理解、视觉识别、坐标选择和 agent 模型都会引入变化，不适合控制 benchmark 的计时区间。测量窗口内的启动、滚动和动画应交给 Macrobenchmark 与 UI Automator；指标由 Macrobenchmark、Perfetto Trace、APA 或线上 APM 给出。冷启动耗时、帧时间分布、CPU 调度、GPU counter、GC 暂停、Binder 等待时间都不能从 Journey 的成功/失败判断中推导。

官方 Journey 页面没有发布固定的 `android journey ...` 子命令格式，这里不构造这类命令。文件格式、运行步骤和 CI 接入方式以 Android CLI 当前版本、Journeys skill 和项目内实际生成文件为准。报告还要记录 CLI、agent、模型、skill 版本或内容快照，避免把不同执行器的结果直接并列。

## Android Studio 语义命令与性能排查协作

`android studio` 命令处于预览状态。官方文档给出的前提是：项目要在 Android Studio Quail 2 Canary 1 或更高版本中打开，并且 Gemini in Android Studio 已启用且已登录。满足这些条件后，agent 可以通过 CLI 连接正在运行的 Android Studio 实例，调用 IDE 的语义能力。

| 命令 | 输出 | 性能排查里的用法 |
|---|---|---|
| `android studio check` | Android Studio PID、版本、打开的项目状态 | 多 IDE 实例时选择目标项目，确认 CLI 与 IDE 已连接 |
| `android studio analyze-file <path>` | Kotlin / Java 文件里的错误、警告、lint | 修改性能相关代码后做 IDE 级静态检查 |
| `android studio find-declaration <symbol>` | 符号声明位置，可用 `--context-file` 消歧 | 从 trace 里的类名、方法名跳到源码定义 |
| `android studio find-usages <symbol>` | 符号引用位置 | 判断某个性能入口是否还有其他调用方 |
| `android studio open-file <path>` | 在 Android Studio 当前编辑器打开文件 | 把 agent 找到的源码、trace、报告交给人工复核 |
| `android studio render-compose-preview <path> <composable>` | Compose Preview PNG，可选语义树 JSON | 改 Compose UI 后做视觉与语义树确认 |
| `android studio version-lookup <artifacts...>` | Maven、AGP、Gradle、NDK、SDK、Compose、Kotlin 等版本信息 | 核对工具链和依赖版本，减少手工查版本带来的误差 |

这组命令适合服务源码定位和人工复核。例如 trace 显示某段 Compose 页面在滑动时产生大量重组，agent 可以先用 `find-declaration` 找到目标 composable，再用 `analyze-file` 检查修改后的文件，再用 `render-compose-preview --print-semantics` 生成预览图和语义树。若 release trace 中的符号已混淆或只剩地址，需要 mapping、native symbol 或源码版本协助定位。帧时间改善仍要回到 trace 或 benchmark 验证。

`version-lookup` 返回仓库或工具渠道中的可用新版本，不保证该版本适合当前项目，也不会替团队选择 stable、beta 或 canary。版本目录、依赖锁、AGP/Gradle 兼容表和回归测试仍是升级依据。

## Android skills 与性能专项能力

Android skills 是面向 AI 工具和 agent 的指令包，用来把 Android 领域里的推荐流程、脚本、模板和参考资料打包给 agent 使用。官方文档列出的能力包括 XML 到 Compose 迁移、AGP 9 升级、Navigation 3、edge-to-edge UI、R8 配置审计等；这些能力都属于“让 agent 更懂 Android 工作流”的层面。

`android init` 是最短的初始化入口，用来安装基础 `android-cli` skill。Android CLI 还提供 `skills list/find/add/remove` 管理能力：

- `android skills list --long`：列出可用 skill、描述和已安装到哪些 agent。
- `android skills find 'performance'`：按描述搜索与性能相关的 skill。
- `android skills add --skill=<skill-name>`：安装或更新单个 skill；省略 `--skill` 和 `--all` 时默认安装 `android-cli` skill。
- `android skills add --all`：一次安装或更新全部 Android skills。
- `android skills remove --skill=<skill-name>`：从一个或多个 agent 目录移除 skill。

更新边界要写进团队规范：官方文档提醒，如果自定义了某个 skill，应改名保存，否则后续 `skills add` 更新时可能被覆盖。项目自定义 skill 放在仓库根目录的 `.skills/` 或 `.agent/skills/` 下，每个目录包含大小写固定的 `SKILL.md`。团队把 Perfetto SQL 模板、R8 审计流程、启动回归脚本放进自定义 skill 时，应使用内部名称，并记录来源和版本。

性能工程里较相关的官方 skill 包括三类：Perfetto SQL 把自然语言问题转换成查询并对本地 trace 执行；Testing setup 生成测试策略和基础结构；R8 auditing 检查压缩配置及相关性能问题。安装或升级后应检查 `SKILL.md`、附带脚本和资源，再允许 agent 执行。当前 CLI 文档只描述“更新到最新版”，没有提供 skill 版本固定参数；需要可重复运行时，把已审核内容的提交或归档留在实验记录中。skill 输出仍要经过 trace 表结构、字段单位、编译模式和设备条件复核。

## 与 APA / Perfetto / Macrobenchmark 的分工

把 Android CLI 放进现有工具箱后，推荐按“环境 → 复现 → 采集 → 分析 → 回归”的顺序组织：

| 阶段 | Android CLI 做什么 | 其他工具做什么 | 产物 |
|---|---|---|---|
| 环境 | `android info`、`android sdk list`、`android emulator list/start` 记录 SDK 和设备 | CI 记录构建号、git commit、设备温度、电量、刷新率 | 环境基线 |
| 复现 | `android run` 安装 APK，Journey 或 screen/layout 驱动页面 | 人工确认测试账号、弱网、权限弹窗等条件 | 页面状态、截图、布局树 |
| 采集 | CLI 触发前置动作和结束动作 | Profiler / Perfetto / APA / Macrobenchmark 采集 trace 或指标 | trace、profile、benchmark JSON |
| 分析 | `android studio find-declaration/find-usages/open-file` 关联源码 | Perfetto SQL、APA、Profiler 做证据分析 | SQL、截图、源码定位 |
| 回归 | agent 准备同一入口状态；计时窗口外可用 Journey | Macrobenchmark 或 CI 门禁对比指标 | 趋势表、阈值判断、失败截图 |

Android CLI 负责准备环境、运行 App 和定位源码。14.17 节的 APA 在同一窗口分析 CPU、GPU、内存、功耗与 SurfaceFlinger；13.9 节的 Perfetto SQL 从 trace 表中计算定量结果；19.11 节的 Macrobenchmark 重复执行受控场景并输出指标。工具之间通过设备基线、APK、操作脚本、trace 和查询关联。

## CI 与本地 agent 工作流模板

一条最小可复现流程可以拆成六类材料：环境记录、项目描述、设备状态、Journey 或操作脚本、trace / benchmark 产物、分析报告。下面的骨架补齐了旧模板遗漏的 AVD 创建前置条件和启动完成检查；真实性能数字仍应在固定的物理设备上采集。

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

`emulator start` 在后台运行，因此脚本要等待 adb 连接和 `sys.boot_completed=1`。这只表示系统完成启动，不表示温度、编译状态、网络和后台任务已经满足性能基线。启动回归可以接 Macrobenchmark；卡顿排查可以接 Perfetto 或 APA；功耗问题还要采集电源、温度和电池数据；Compose UI 变更可以接 `android studio render-compose-preview`。

## 隐私与遥测边界

Android CLI 官方文档写明会收集基础使用数据，包括 `android` 命令和子命令调用、非位置参数或选项名、固定枚举类系统选项值，以及经过匿名化处理的堆栈和异常消息。文档同时写明不会收集命令响应，也不会收集用户创建的输入或外部标识符，例如 Maven 坐标、文件路径、自定义项目名等参数值。

企业内网使用时，报告里应单独记录三类内容：

- 命令日志：是否包含本地路径、包名、账号、设备 serial、截图或布局树里的业务数据。
- agent 上下文：是否把 trace、截图、布局树、源码片段交给外部模型。
- skill 来源：官方 skill、团队内部 skill、第三方 skill 分开管理，更新记录要可追溯。

`screen capture` 和 `layout` 会直接读取设备画面和 UI 树，风险高于 `android info` 或 `sdk list`。Perfetto SQL skill 还可能读取本地 trace，Journey agent 会接收自然语言步骤与设备视觉信息。涉及用户数据、测试账号、订单页、聊天页、健康数据等页面时，应使用隔离测试环境，并在报告发布前做脱敏处理。

## 小结

Android CLI 为 agent 提供项目描述、SDK 与设备管理、UI 状态读取和 IDE 语义入口。它能让复现输入更完整，但截图、布局树和 Journey 成功都不构成性能结论。Android 17 上的结果应绑定 CLI 版本、`android-17.0.0_r1` 设备平台、`android17-6.18-2026-06_r6` 内核或实际 vendor kernel，再由 Profiler、Perfetto、APA、Macrobenchmark 或线上指标验证。

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
