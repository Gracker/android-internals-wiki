---
title: "DoraemonKit / DoKit"
chapter: "19"
section: "19.07"
status: ready-for-review
drafted_date: "2026-04-24"
drafted_by: "codex"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-24"
last_verified_against: "didi/DoKit GitHub README"
confidence: medium
tags: [apm, debug-tools, testing, mock, weak-network]
related_chapters: ["19.0"]
sources:
  - type: blog
    path: "https://github.com/didi/DoKit"
pipeline_stage: task9_pending
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-04-24"
task9_state: pending
task2b_state: pending
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

如果团队把 DoKit 当线上 APM 用，后面会遇到采样、上报、数据合规、用户影响、开关控制等问题。它可以帮助开发和测试更快复现线上问题，但不应该直接承担线上采集职责。

## 和 Android Studio Profiler、Perfetto 的关系

DoKit 适合“边操作边看”。Android Studio Profiler 和 Perfetto 适合“抓一次完整证据后分析”。

一个常见流程是：测试同学用 DoKit 在端上发现某页面滑动时 FPS 下跌，并记录操作路径；开发同学用同一操作路径抓 Perfetto，再看主线程、RenderThread、GPU 和调度；修复后再用 DoKit 做快速回归。这样 DoKit 负责入口，Perfetto 负责证据。

## 接入建议

DoKit 最好只进入 Debug、internal、QA 渠道包，并且把入口做成明确的研发开关。网络监控、弱网、函数耗时、卡顿抓栈这类能力可能影响性能，不能在日常开发包里全量常开。

团队可以把 DoKit 当作“公共研发面板”：统一环境切换、日志查看、沙盒文件、网络请求和基础性能观察。这样比每个业务线各自实现一套调试入口更容易维护，也能减少测试现场来回装工具的时间。

## Debug 工具箱的工程结构

DoKit 这类工具通常由三块组成：

- **入口层**：悬浮窗、面板、手势入口、快捷按钮。
- **采集层**：FPS、CPU、内存、网络、Crash、启动、UI 层级、函数耗时等模块。
- **扩展层**：业务自定义工具、环境切换、Mock、沙盒浏览、日志查看。

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

DoKit 的性能数据适合“现场判断”，不适合直接写入最终分析结论。原因是端上悬浮窗和采集逻辑本身也会消耗资源。

读这些数据时要按层级使用：

| 数据 | 适合用途 | 需要复核 |
|---|---|---|
| FPS 曲线 | 快速发现某个操作顿挫 | 用 JankStats / Perfetto 校验帧边界 |
| CPU / 内存 | 判断是否有明显资源上涨 | 用 Profiler / dumpsys / Perfetto 复核 |
| 网络列表 | 联调接口、检查大包体或失败请求 | 用网络库日志和服务端监控复核 |
| 启动耗时 | QA 回归中的粗粒度对比 | 用 Macrobenchmark / `am start -W` / Perfetto 复核 |
| UI 层级 | 发现布局过深或控件异常 | 用 Layout Inspector / trace 复核 |

这个分工能避免测试现场“看到数值异常就直接定因”。DoKit 给的是入口，不是最终证据。

## 弱网和 Mock 的价值

性能问题经常被网络状态放大。DoKit 的弱网、Mock、网络查看能力可以让测试人员复现这些场景：

- 接口慢导致首屏等待。
- 图片大导致列表滑动期间解码和网络竞争。
- 弱网重试导致主线程回调堆积。
- Mock 数据量过大导致 adapter diff 或布局成本上升。

这些场景靠线上 APM 很难直接复现。DoKit 的价值在于让测试和开发在同一个包里快速切换条件，把“用户反馈偶现慢”转成可操作路径。

## Release 隔离清单

如果项目集成 DoKit，要检查 Release 包是否完全隔离：

- 依赖没有进入 Release runtime classpath。
- 悬浮窗权限、辅助功能权限、网络代理能力没有出现在正式包流程。
- Mock、环境切换、数据库查看、沙盒浏览不能被用户触发。
- 混淆规则没有因为 Debug 工具放宽太多业务类。
- 自定义工具注册点不会保留敏感菜单或调试账号。

这些不是“安全洁癖”。调试工具常带有文件、网络、日志和环境切换能力，进入正式包后风险比普通性能 SDK 高。

## 推荐使用方式

DoKit 最适合变成团队统一的 QA 包能力。每个性能敏感业务可以注册自己的小工具，例如：

- 清理指定业务缓存。
- 切换接口环境。
- 打开当前页面的内部状态面板。
- 手动触发一次资源预加载。
- 导出当前页面日志和关键性能点。

这样测试人员不用知道每条 adb 命令，开发人员也能把临时调试代码收敛到统一入口里。对技术书稿来说，DoKit 更适合作为“如何把研发现场的诊断入口工程化”的案例，而不只是某个 FPS 功能。
