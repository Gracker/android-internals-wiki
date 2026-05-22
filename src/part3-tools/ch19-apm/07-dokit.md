---
title: "DoraemonKit / DoKit"
chapter: "19"
section: "19.07"
status: finalized
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "版本需按 artifact / AndroidX / Gradle / AGP 单独验证；README 明确覆盖 3.5.0 / 3.5.0.1 与 AGP 3.3.0+"
last_verified: "2026-04-27"
last_verified_against: "didi/DoKit README + Android/README + DoKitPlugin.kt + Okhttp3ClassTransformer.kt + PerformanceDataManager.java"
confidence: medium
tags: [apm, debug-tools, testing, mock, weak-network]
related_chapters: ["19.0"]
sources:
  - type: official
    path: "https://github.com/didi/DoKit/blob/master/README.md"
  - type: official
    path: "https://github.com/didi/DoKit/blob/master/Android/README.md"
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task6_reviewed_date: "2026-04-27"
task6_result: "pass-light-edit"
last_task6_audit: "2026-05-20"
reviewed_by: openclaw-task6
reviewed_date: "2026-04-25"
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_date: "2026-04-27"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-04-27T11:27:00+08:00"
last_task9_audit: "2026-05-22"
task2b_result: fixed
task2b_state: fixed
review_round: 3
last_task2b_at: "2026-04-27T04:40:00+08:00"
review_notes: "2026-04-27 Task9 复审通过：DoKit README 版本矩阵、registerTransform/AGP8 风险、OkHttp ASM 注入、PerformanceDataManager 采样口径与 dokit.cn 出站边界已覆盖。"
---

# DoraemonKit / DoKit

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 [定位] 说明 DoKit 是研发现场工具箱，主要提高调试和 QA 效率，不承担线上指标平台职责。
- 🔹 [能力地图] 按性能面板、网络、Mock、弱网、日志、业务入口、环境切换、视觉辅助拆功能和使用对象。
- 🔹 [性能可信度] 说明 FPS、CPU、内存、网络数据的采集来源、刷新频率、误差和适合回答的问题。
- 🔹 [工具关系] 和 Android Studio Profiler、Perfetto、JankStats、FrameMetrics 做分工表，写清 DoKit 何时只能当初筛工具。
- 🔹 [接入结构] 展开 Debug-only 依赖、模块注册、业务入口封装、no-op 实现和多 flavor 管理。
- 🔹 [弱网 / Mock] 说明它们对复现网络慢、接口异常、缓存策略、页面降级的价值；补一个测试场景。
- 🔹 [Release 隔离] 给检查清单：依赖隔离、入口隐藏、权限、日志、网络代理、Mock 数据、隐私字段。
- 🔹 [团队协作] 写清测试、开发、性能专项人员分别怎样使用 DoKit，避免只列功能。
- 🔹 [安全风险] 覆盖内网地址、接口 token、用户数据、调试入口被误带到线上包的风险。
- 🔹 [推荐方式] 给“DoKit 发现异常 -> 复现 -> Perfetto / Profiler 深查 -> 修复验证”的使用路径。

### 扩展（可选深入）

- 🔸 增加一个工具箱注册示例，展示如何把业务诊断入口收拢到统一面板。
- 🔸 补充弱网、Mock、接口环境切换的测试用例表。
- 🔸 对 DoKit upstream README、版本状态、Android Gradle 插件适配做核对。
- 🔸 增加与 Flipper、Stetho、Android Studio 工具的差异说明。
- 🔸 补一个 Release 包检查脚本或 Gradle 约束示例。

### 流水线加工要求

- DoKit 的每个能力都要写“适合现场”和“不适合结论”，不要把面板数据写成线上指标。
- 涉及 Release 风险的内容必须给可执行检查项。
- 示例应服务于团队工作流，不要只展示悬浮窗截图式描述。

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## DoKit 是研发现场工具箱

DoKit，也就是 DoraemonKit，是滴滴开源的泛前端研发效率平台。Android 侧包含 App 信息、沙盒浏览、弱网、Crash 查看、数据库查看、网络监控、帧率、CPU、内存、卡顿、启动耗时、UI 层级、函数耗时、内存泄漏等工具。

它的定位偏 Debug 和 QA 现场。官方 README 也明确提醒：功能只针对 Debug 环境，Release 环境没有经过充分验证，不建议在 Release 使用。

## 能力地图：谁在现场用 DoKit

DoKit 的价值不只在性能面板。它更像一个把调试入口、测试条件和现场记录放到同一个包里的工具箱。

| 能力 | 使用对象 | 回答的问题 |
|---|---|---|
| 性能面板 | 开发、性能专项 | 页面操作时 FPS、CPU、内存、启动耗时是否异常 |
| 网络查看 | 测试、开发 | 请求参数、响应内容、耗时、图片大小是否异常 |
| Mock | 测试、开发 | 异常响应、空态、大数据量页面能否稳定复现 |
| 弱网 | 测试、性能专项 | 首屏等待、重试、降级策略在慢网下是否稳定 |
| 日志 / 沙盒 | 开发、测试 | 本地缓存、文件、日志和运行状态是否符合预期 |
| 业务入口 | 开发、测试 | 环境切换、清缓存、内部状态页是否收在一个面板里 |
| 视觉辅助 | 开发、UI QA | UI 层级、控件信息、布局边界是否异常 |

## 性能能力覆盖哪些场景

DoKit 的性能检测能力更像“端上小仪表盘”，适合开发和测试人员快速发现异常：

| 能力 | 适合的现场 | 产出 |
|---|---|---|
| 帧率 / CPU / 内存 | 页面滑动、复杂动画、长时间使用 | 端上曲线和当前数值 |
| 流量监控 | 接口联调、图片加载、弱网测试 | 请求列表、概要和详情 |
| 卡顿 | 手工操作复现顿挫 | 当前堆栈或卡顿记录 |
| 启动耗时 | 每日构建包回归 | 启动阶段耗时 |
| UI 层级检查 | 布局过深、过度绘制疑似问题 | 页面层级和控件信息 |
| 函数耗时 | 局部代码路径慢 | 方法耗时报告 |

这些能力的共同特点是反馈快。开发者不需要打开多个外部工具，也不用先搭平台，就能在端上拿到第一批线索。

## 它不适合替代线上 APM

DoKit 的强项是现场效率，不是生产监控。原因有三点：

- 功能面板、浮窗、hook、网络代理等能力会改变 App 运行环境。
- Debug 工具更重，开销和兼容性不适合默认带到线上。
- 它输出的是端上观察结果，不是稳定的版本级指标体系。

实现策略也要分开看。DoKit 在 Debug 包里使用 500ms/1000ms 轮询、运行时 hook 和编译期 ASM 插桩，优先换取现场可见性；线上 APM 要控制探针开销、采样率和出站数据，常见做法是更窄的埋点、native hook、系统信号或按需采样。两类工具的数据口径不能混用。

如果团队把 DoKit 当线上 APM 用，后面会遇到采样、上报、数据合规、用户影响、开关控制等问题。它可以帮助开发和测试更快复现线上问题，但不应该直接承担线上采集职责。

## 和 Android Studio Profiler、Perfetto、JankStats、FrameMetrics 的关系

DoKit 适合“边操作边看”。Android Studio Profiler、Perfetto、JankStats 和 FrameMetrics 适合在同一复现路径下补证据。

| 工具 | DoKit 先做什么 | 何时切过去 |
|---|---|---|
| Android Studio Profiler | 在端上确认 CPU、内存、网络和页面路径是否异常 | 要看方法调用、对象分配、线程状态或网络详情 |
| Perfetto | 记录复现步骤和异常发生的大致时间点 | 要确认主线程、RenderThread、GPU、sched、FrameTimeline 等系统级证据 |
| JankStats | 先定位容易掉帧的页面和操作条件 | 要在 App 侧按页面、状态和交互标签采集 jank 事件 |
| FrameMetrics | 先判断某个窗口是否有帧率异常 | 要拿窗口级 frame duration，以及 layout、draw、sync 等阶段耗时 |

一个常见流程是：测试同学用 DoKit 在端上发现某页面滑动时 FPS 下跌，并记录操作路径；开发同学用同一操作路径抓 Perfetto，再看主线程、RenderThread、GPU 和调度；修复后再用 DoKit 做快速回归。这样 DoKit 负责入口，Perfetto 负责证据。

## 接入建议

DoKit 最好只进入 Debug、internal、QA 渠道包，并且把入口做成明确的研发开关。网络监控、弱网、函数耗时、卡顿抓栈这类能力可能影响性能，不能在日常开发包里全量常开。

团队可以把 DoKit 当作“公共研发面板”：统一环境切换、日志查看、沙盒文件、网络请求和基础性能观察。这样比每个业务线各自实现一套调试入口更容易维护，也能减少测试现场来回装工具的时间。

## 版本说明与构建边界

upstream 文档给的是构建兼容表，不是一个统一的“Android 8-17 都能用”承诺。当前 README 明确列出的信息如下：

| 线路 | 依赖与 groupId | 构建前提 | 适用说明 |
|---|---|---|---|
| AndroidX 新线 | `io.github.didi.dokit:dokitx:3.5.0` 与配套 `dokitx-plugin` | Gradle 6.8 及以上，AGP 3.3.0+，仓库切到 `mavenCentral()` | README 把它作为当前 AndroidX 主线，Release 使用 `dokitx-no-op` |
| AndroidX 兼容线 | `io.github.didi.dokit:dokitx:3.5.0.1` 与配套 plugin | Gradle 6.8 及以下，AGP 3.3.0+ | Android README 把这条线留给较旧的 Gradle 环境 |
| 旧 groupId / support | `com.didichuxing.doraemonkit` 3.3.5 | 旧 AndroidX 或 support 工程 | upstream 写明 support 已停止更新，迁移后再继续接入 |

Android 侧运行兼容性还要继续分开验证。README 没有单独给出 AGP 8.x、targetSdk 35+、Android 15-17 的兼容承诺，所以更稳的写法是：把 DoKit 当成“按构建工具链逐项目验证”的 Debug 能力，而不是写成一个统一的系统版本范围。

## Debug 工具箱的工程结构

DoKit 这类工具通常由三块组成：

- **入口层**：悬浮窗、面板、手势入口、快捷按钮。
- **采集层**：FPS、CPU、内存、网络、Crash、启动、UI 层级、函数耗时等模块。
- **扩展层**：业务自定义工具、环境切换、Mock、沙盒浏览、日志查看。

源码阅读时要把运行时采集和编译期插件分开：

| 位置 | 入口 | 读法 |
|---|---|---|
| Gradle 插件入口 | `Android/dokit-plugin/src/main/kotlin/com/didichuxing/doraemonkit/plugin/DoKitPlugin.kt` | `apply()` 中按 application / library 分支注册 `DoKitCommonTransform`，并读取 `DOKIT_METHOD_SWITCH`、`DOKIT_WEBVIEW_CLASS_NAME` 等开关。 |
| OkHttp 注入 | `Android/dokit-plugin/src/main/kotlin/com/didichuxing/doraemonkit/plugin/transform/classtransform/Okhttp3ClassTransformer.kt` | 匹配 `okhttp3.OkHttpClient` 构造方法，在 `networkInterceptors` 写入后插入 `OkHttpHook.addDoKitIntercept(OkHttpClient)`。 |
| 性能面板采样 | `Android/dokit/src/main/java/com/didichuxing/doraemonkit/kit/performance/PerformanceDataManager.java` | 统一处理 FPS、CPU、内存、网络流量采样，是判断面板数据可信度的入口。 |

README 写 AGP 3.3.0+，但源码仍有 `registerTransform` 路径；AGP 8.x 项目要按实际插件版本和构建日志验证，不能只按 README 推断兼容性。

这三层要和业务代码隔离。推荐做法是只在 Debug / QA flavor 引入 DoKit 依赖，业务模块通过接口注册自定义工具，Release flavor 使用 no-op 实现。

```kotlin
interface DevToolRegistry {
    fun registerPanel(name: String, action: () -> Unit)
}

class NoopDevToolRegistry : DevToolRegistry {
    override fun registerPanel(name: String, action: () -> Unit) = Unit
}
```

这样业务代码可以保留调试入口注册点，但 Release 包不会带入 DoKit 面板和相关采集逻辑。

## 性能面板的数据可信度

DoKit 的性能数据适合现场判断，不适合直接写入最终分析结论。端上浮窗、后台 Handler 轮询、Choreographer 回调和编译期插桩都会改变运行环境。

读这些数据时要先看采集口径：

| 指标 | 源码入口 | 采集方式与刷新频率 | 误差来源 | 复核工具 |
|---|---|---|---|---|
| FPS | `PerformanceDataManager#startMonitorFrameInfo()` / `FrameRateRunnable` | 主线程 `Choreographer.FrameCallback` 统计，`FPS_SAMPLING_TIME = 1000` ms | 浮窗绘制、主线程回调排队、刷新率变化；只给每秒帧数，不给 FrameTimeline 里的 jank 类型 | JankStats / Perfetto FrameTimeline |
| CPU | `PerformanceDataManager#executeCpuData()` | Android O+ 执行 `top -n 1`；低版本读 `/proc/stat` 和 `/proc/<pid>/stat`；`NORMAL_SAMPLING_TIME = 500` ms | `top` 执行成本、短尖峰被平均、按 CPU 核数归一化后的口径差异 | Android Studio Profiler / Perfetto sched |
| 内存 | `PerformanceDataManager#getMemoryData()` | Android P 之后走 `Debug.getMemoryInfo()`；较低版本走 `ActivityManager.getProcessMemoryInfo()`；500 ms 轮询 | PSS 更新频率、GC 时机、系统 API 限流；不能直接解释对象引用关系 | Profiler / `dumpsys meminfo` / HPROF |
| 网络流量 | `startMonitorNetFlowInfo()` / `NetworkManager#getTotalRequestSize()` / `Okhttp3ClassTransformer` | Handler 每 500 ms 读取请求和响应累计字节；OkHttp 侧通过编译期 ASM 插入 `OkHttpHook.addDoKitIntercept()` | 只覆盖被 hook 的网络栈；Interceptor 自身有开销；无法拆 DNS、connect、TLS 等阶段 | OkHttp `EventListener` / 网络库日志 / 服务端 trace |
| 启动耗时 | 启动模块与插件配置，按接入版本核对 | 按阶段事件计时，不属于固定 500 ms 轮询 | Debug 包、冷启动 / 温启动状态、插件插桩都会影响耗时 | Macrobenchmark / `am start -W` / Perfetto |

这张表把“DoKit 只能初筛”的原因落到实现上：FPS 是主线程帧回调统计，CPU / 内存是进程级采样，网络依赖 OkHttp 注入和流量累计。它们能帮助复现路径和缩小范围，定因仍要回到专项工具。

## 弱网和 Mock 的价值

性能问题经常被网络状态放大。DoKit 的弱网、Mock、网络查看能力可以让测试人员复现这些场景：

- 接口慢导致首屏等待。
- 图片大导致列表滑动期间解码和网络竞争。
- 弱网重试导致主线程回调堆积。
- Mock 数据量过大导致 adapter diff 或布局成本上升。

这些场景靠线上 APM 很难直接复现。DoKit 的价值在于让测试和开发在同一个包里快速切换条件，把“用户反馈偶现慢”转成可操作路径。

## 平台网络上报与合规边界

README 的“使用提醒”单独写明：SDK 会配合 `dokit.cn` 平台产生网络数据。官方列出的出站类型有四类：

- 集成统计：`DoraemonStatisticsUtil#uploadUserInfo`
- 内置 kit 使用统计：`DataPickManager#realPost`
- 健康体检上传：`AppHealthInfoUtil#post`
- 数据 Mock 相关请求：`NetWorkMockFragment` 中的接口

这会改变“DoKit 只是本地调试面板”的风险边界。只隐藏悬浮窗还不够，内网测试包上线前至少要补三项检查：

- 是否真的需要 `productId()` 和平台工具；不需要的平台能力用抓包再确认一次。
- 是否把 DoKit 请求纳入测试包的出站域名白名单、代理规则和隐私审查。
- 截图、日志导出、抓包面板里是否暴露内网地址、Header、token、用户标识。

## Release 隔离清单

如果项目集成 DoKit，要检查 Release 包是否完全隔离：

- 构建依赖：`releaseImplementation` 或正式 flavor 明确切到 `dokitx-no-op`，CI 再检查 release dependency tree 里没有 `dokitx` 本体和调试面板资源。
- 入口与权限：悬浮窗、辅助功能、网络代理、文件浏览、环境切换入口都不能出现在正式包流程里。
- 平台出站：正式包不保留 `productId()`、健康体检、Mock、统计上报这类平台能力，测试包上线前先做一次抓包留档。
- 数据与日志：抓包详情、Header、token、用户标识、内网地址、沙盒导出文件不能被普通用户触发，也不要出现在对外截图里。
- 业务扩展：自定义工具注册点、测试账号菜单、后门手势和调试 deep link 不留到正式包。

一个常见事故形态是：灰度包误带测试入口，排查同学把环境切到测试域名或打开 Mock，结果真实账号走到了错误接口；另一个常见情况是抓包截图带出 token 和内网地址。DoKit 的风险不在某个单独面板，而在它把网络、文件、环境切换和日志放进了同一个入口里。

## 团队协作与推荐使用方式

DoKit 放进团队流程里时，三类角色的分工会更清楚：

| 角色 | 先用 DoKit 做什么 | 后续工具 |
|---|---|---|
| 测试 | 复现弱网、Mock、环境切换，导出请求和操作路径 | 把稳定复现步骤交给开发或性能专项 |
| 开发 | 看网络列表、页面状态、沙盒文件、临时业务面板 | 用 Profiler、日志、代码断点定位实现细节 |
| 性能专项 | 用 DoKit 固化操作路径，确认问题只在某页面或某接口条件下出现 | 用 Perfetto、FrameTimeline、Macrobenchmark 做定量分析 |

每个性能敏感业务还可以注册自己的小工具，例如：

- 清理指定业务缓存。
- 切换接口环境。
- 打开当前页面的内部状态面板。
- 手动触发一次资源预加载。
- 导出当前页面日志和关键性能点。

推荐路径可以写成一条固定动作链：

1. 用 DoKit 发现异常，记下页面、手势、账号和网络条件。
2. 用弱网、Mock、环境切换把现场复现稳定下来。
3. 在同一操作路径下切到 Perfetto 或 Profiler 抓完整证据。
4. 修复后回到 DoKit 做冒烟回归，再用专项工具复核。

这样测试人员不用记 adb 命令，开发人员也能把临时诊断入口收拢到统一面板里。DoKit 负责把问题复现稳定，后面的定因和定量仍然交给 Perfetto、Profiler、JankStats 或基准测试工具。
