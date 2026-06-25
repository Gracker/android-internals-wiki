---
title: "持续性能验证与 CI/CD"
chapter: "27.5"
section: "第三部分：工具与方法论"
status: ready-for-review
drafted_date: "2026-06-21"
drafted_by: "openclaw"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-21"
last_verified_against: "ThoughtWorks 性能工程成熟度模型；Android Developers Macrobenchmark / benchmarking in CI / Android Vitals docs"
confidence: medium
sources:
  - type: blog
    path: "https://www.thoughtworks.com/zh-cn/insights/blog/platforms/performance-engineering-maturity-model"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/benchmarking-in-ci"
  - type: official
    path: "https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
  - type: official
    path: "https://developer.android.com/topic/performance/vitals"
tags: [performance-engineering, ci-cd, macrobenchmark, release-gate, regression-detection]
related_chapters: ["15.10", "26.7", "19.14", "26.15"]
---

# 持续性能验证与 CI/CD

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 持续性能验证是 DevPerfOps 的工程载体：每次性能变化都要有记录、阈值、趋势和归因线索。
- 构建阶段处理体积、资源、R8、Compose compiler metrics 等低噪声检查。
- 测试阶段用 Macrobenchmark、Microbenchmark、泄漏巡检和 trace 报告覆盖关键路径。
- 发布阶段用 performance scorecard 汇总启动、流畅性、内存、网络、功耗和体积风险。
- 灰度和线上阶段把真实用户指标纳入验证，并把报警自动关联 commit、实验、设备段和 owner。

<!-- outline-end -->

持续性能验证把性能检查放进 CI/CD，让回归在合入、构建、测试、发布和灰度阶段被发现。它的目标是让每次性能变化都有记录、有阈值、有趋势、有归因线索；CI 不承担拦住所有性能问题的职责。

Android 性能 CI 的难点比单元测试高很多：设备状态会波动，温度会影响 CPU 频率，系统后台任务会干扰帧时间，网络和账号数据会改变结果。持续验证要承认噪声，并通过固定设备、重复运行、历史趋势和失败分级降低误判。

如果把性能工程看成 DevPerfOps 闭环，CI/CD 负责连接“开发中的性能假设”和“运行中的性能事实”。设计阶段定义的预算进入 benchmark，benchmark 结果进入发布 scorecard，灰度和线上观测再反向修正预算和测试场景。闭环跑不起来时，性能 CI 只会变成一组没人维护的红绿灯。

## 构建阶段：先拦住静态退化

构建阶段适合执行成本低、结果稳定的检查。它不需要真机，也不依赖运行时场景，适合放在 PR 或 merge request 上。

APK 和 AAB 体积回归检测是最直接的检查。CI 可以用 bundletool、APK Analyzer 或自研 Gradle task 输出 base module、dynamic feature、Dex、resources、assets、native so、字体和图片增量。规则应按模块显示 owner，例如“商品详情模块新增 420 KB 图片资源，超过 200 KB 预算，需要说明来源和压缩策略”。

R8 / ProGuard 规则验证也应进入构建阶段。错误的 keep 规则会阻止代码裁剪，反射框架、序列化、路由和插件系统常把 keep 范围写得过宽。CI 可以比较 mapping、usage.txt 和 dex method count，发现大面积保留时要求评审。对 SDK 接入，必须检查是否引入重复依赖和多 ABI native so。

资源检查可以覆盖图片尺寸、透明通道、重复资源、未使用资源、Lottie 大小、vector path 复杂度和 layout 层级风险。过度绘制很难完全静态判断，但资源和布局膨胀可以提前发现。对 Compose 项目，构建阶段还可以开启 compiler metrics，跟踪 unstable 参数、skippable/composable 数量和模块变化趋势。

## 测试阶段：让 benchmark 成为代码

测试阶段负责运行真机或模拟器性能场景。Jetpack Macrobenchmark 是 Android 团队做持续验证的主力工具，适合启动、滚动、页面切换和关键交互。19.14 已经说明 Microbenchmark 与 Macrobenchmark 的边界；CI 中要优先覆盖用户可感知路径。

Macrobenchmark in CI 的工程结构通常包括独立 `benchmark` module、接近发布的 target app variant、固定测试账号、固定 mock 或 staging 数据、设备池和结果上传任务。每个 benchmark 用例应声明场景、准备数据、指标、重复次数和失败阈值。报告里至少保留 median、P90/P95、标准差、设备、系统版本、温度状态、commit 和 trace 文件。

启动回归门禁要特别谨慎。cold start 受编译模式、安装状态、profile、系统缓存和账号数据影响。CI 可以用 `CompilationMode.Partial` 验证 Baseline Profiles，也可以用 `None` 暴露未编译路径成本，但不同模式不能混在同一趋势图里比较。失败时，报告应给出启动阶段拆分：process start、ContentProvider、Application、first Activity、first draw、关键内容完成。

内存泄漏检测可以放在 nightly 或预发流水线。LeakCanary 不适合直接作为所有 PR 的硬门禁，但可以对核心页面跑自动打开、关闭、强制 GC、等待引用释放的脚本，并把可疑泄漏上报。KOOM、heapprofd 或自研 native 内存采样适合更重的预发巡检，重点看图片、WebView、播放器和地图场景。

## 发布阶段：性能 scorecard

发布阶段不应重新发现基础问题。它要把前面各阶段结果汇总成发布判断。26.7 的 release quality gate 可以扩展出性能 scorecard，作为版本放量前的检查表。

一个 Android release performance scorecard 可以包含：

- 启动：本版本与上个稳定版本 cold/warm/hot start 对比，核心设备段 P50/P95 是否在预算内。
- 流畅性：首页、详情、搜索、支付等路径的 slow frame、frozen frame 和 trace 异常。
- 内存：低端机 PSS、Java heap、native heap、OOM、泄漏巡检结果。
- 网络：核心接口数量、payload、超时、弱网成功率和后端 P95。
- 功耗：后台任务、wake lock、定位、前台服务和 Android Vitals 风险。
- 包体积：base 下载体积、Dex、resources、native so 和动态模块增量。

scorecard 的价值在于决策，不在于表格漂亮。每个红项都应对应处理结论：修复、回滚、灰度观察、远程降级或有时限豁免。没有结论的红项会削弱门禁权威。

## 灰度与线上：把真实用户纳入验证

线下验证通过后，灰度阶段要比较 canary 与 stable。A/B 性能对比需要控制变量：同一设备段、同一国家、同一网络类型、同一实验配置、同一时间窗口。若 canary 用户同时进入多个产品实验，性能数据需要标注实验桶，否则容易把推荐策略或后端波动误判成客户端回归。

Android Vitals 可以作为发布后监控的外部信号，覆盖 ANR、crash、excessive wakeups、stuck wake locks、slow rendering 和 frozen frames 等质量指标。自研 dashboards 则补足业务页面、启动阶段、网络接口、内存水位和实验维度。两类看板最好互相引用：Vitals 发现某设备段 bad behavior rate 上升时，内部看板应能查到版本、页面、国家和疑似改动。

自动创建性能 issue 是 L3 以后很有价值的能力。报警触发后，系统自动生成包含指标变化、影响用户量、设备分布、版本范围、相关 commit、实验配置、trace 或日志样本的 issue，并分配给模块 owner。这样性能工程师不用在每次报警后手工拼证据。

## 基础设施：benchmark-as-code

持续性能验证要长期维护，必须把场景和阈值代码化。benchmark-as-code 的含义是：性能场景、设备矩阵、预算阈值、数据准备和报告格式都在仓库里版本化，跟业务代码一起 review。新增核心页面时必须补 benchmark；删除页面时同步删除场景；预算变化需要 PR 说明。

结果存储要支持趋势分析。单次 CI 报告只能告诉团队这次过没过，长期数据库能回答“这个指标从哪个 commit 开始慢慢变差”。常见存储字段包括 commit、branch、build variant、device、API level、thermal status、metric、median、p95、stddev、trace URL 和 owner。趋势图要能按设备、版本和场景过滤。

失败判定建议分三层：单次超过硬阈值直接失败；超过历史均值一定比例时要求重跑；连续多次轻微退化时生成提醒。这样既能拦住大回归，也能发现慢性退化。Android 性能 CI 最怕团队因为误报太多而关闭门禁，偶发误报本身反而可控。

## 持续验证的边界

CI/CD 只能覆盖被写成场景的路径。冷门页面、复杂登录态、第三方 SDK 后台行为、ROM 兼容性和极端弱网仍需要线上观测。持续性能验证要与 15.10 的治理和 26.7 的发布门禁一起工作：CI 提供早期信号，灰度提供真实信号，线上可观测性提供规模化信号。

当三类信号互相矛盾时，以场景和口径排查，而不是直接相信某一个数字。实验室 median 变好但线上 P95 变差，可能说明低端设备或特定网络被遗漏；CI 失败但线上无感，可能是设备池噪声或测试数据问题。持续验证的成熟标志，是团队能解释差异，并把解释转化为更好的场景、预算和看板。
