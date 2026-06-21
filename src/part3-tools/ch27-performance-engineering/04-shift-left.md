---
title: "左移性能工程"
chapter: "27.4"
section: "27.4"
status: ready-for-review
drafted_date: "2026-06-21"
drafted_by: "openclaw"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-21"
last_verified_against: "ThoughtWorks 性能工程成熟度模型；Android Developers performance / profiling / baseline profiles docs"
confidence: medium
sources:
  - type: blog
    path: "https://www.thoughtworks.com/zh-cn/insights/blog/platforms/performance-engineering-maturity-model"
  - type: official
    path: "https://developer.android.com/topic/performance"
  - type: official
    path: "https://developer.android.com/studio/profile"
  - type: official
    path: "https://developer.android.com/topic/performance/baselineprofiles/overview"
tags: [performance-engineering, shift-left, code-review, architecture-review, profiling]
related_chapters: ["15.6", "14.1", "8.1", "19.15"]
pipeline_stage: task9_pending
task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-06-21
last_task6_at: 2026-06-21T15:06:00+08:00
task9_state: pending
---

# 左移性能工程

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 左移的核心是把性能建模、风险识别和轻量 profiling 放进设计、开发和测试阶段。
- 设计评审先处理数据加载、缓存、资源、导航、生命周期和降级策略。
- 代码评审检查主线程、分配、I/O、数据库、图片资源、Compose 重组和启动任务。
- 开发自测用轻量工具发现异常，测试阶段再用 benchmark 和 UI 自动化固化证据。
- 左移不能替代 CI 和线上观测，它负责降低问题进入后段的概率。

<!-- outline-end -->

左移性能工程的目标是在问题进入线上之前降低修复成本。Android 性能问题越晚发现，修复成本越高：需求阶段改一个交互流程可能只要半天，发布前发现启动回归可能需要跨多个团队排查，线上发现低端机 OOM 还要承受灰度、回滚和用户损失。

左移要把性能判断嵌入设计评审、代码评审、开发自测和自动化测试，并不要求每个业务开发者都成为 Perfetto 专家。团队需要给开发者可操作的检查项、工具路径和失败处理方式。

ThoughtWorks 模型把性能工程覆盖到架构设计、研发编码、测试看护和持续运营。左移关注的是前半段：把性能建模前置到需求和架构评审，把专家经验变成普通开发者能执行的 checklist，再用工具把高频检查自动化。这样性能工程不再依赖“发布前找高手看一眼”。

## 设计阶段：先评估性能风险

设计阶段最容易改变架构形态。一个页面是一次性拉全量数据，还是分页加载；图片是服务端裁剪，还是客户端解码后缩放；动画是属性动画，还是复杂 Lottie；导航是单 Activity 多 Fragment，还是多 Activity；这些决定一旦进入编码，后续优化只能补救。

Android 技术设计评审至少要覆盖数据加载、缓存、资源、导航和生命周期。

数据加载要检查接口数量、串并行关系、首屏必需字段、分页策略和失败降级。首页常见问题是多个模块各自请求，最终主线程等待多个回调拼装 UI；更稳的设计是区分关键内容和延迟内容，关键内容优先渲染，推荐、广告、浮层和埋点后置。数据库也要在设计阶段决定是否需要索引、分页查询、事务批处理和 Room 查询线程约束。

缓存策略要说明缓存对象、生命周期和失效条件。图片、用户资料、配置、推荐结果和 WebView 资源不能共享一个模糊的“本地缓存”概念。缓存过小会造成网络和解码抖动，缓存过大会推高 PSS 和 OOM 风险。设计评审应要求给出上限、淘汰策略和低内存处理。

资源和动效要评估首屏成本。大图、长 Lottie、复杂 vector drawable、透明叠层和阴影都可能影响首帧和滑动。设计稿中的动效需要说明帧率目标、持续时间、是否可跳过、是否与列表滚动同时发生。对低端设备，可以在资源层准备降级版本。

导航和生命周期决定对象存活时间。过深 Fragment 嵌套、多个 ViewPager2 同时预加载、页面离开后协程仍持有 View、Compose 状态提升过度，都会让内存和重组成本失控。评审时要确认页面退出后哪些对象应释放，哪些任务应取消，哪些数据可跨页面复用。

## 代码评审：把性能风险写进 checklist

代码评审阶段适合发现局部风险。评审者不需要每次跑完整 benchmark，但应该能识别常见 Android 性能坏味道。

主线程检查是第一类。代码里出现 `SharedPreferences.commit()`、数据库查询、文件读写、Bitmap 解码、JSON 大对象解析、同步 Binder 调用和 `runBlocking` 时，需要确认它们是否运行在主线程。Kotlin 协程并不自动保证后台执行，`Dispatchers.Main` 下调用阻塞函数仍然会卡帧。

分配检查是第二类。列表绑定、`onDraw()`、Compose `@Composable` 高频重组路径和动画回调里不应创建大量临时对象。`String.format()`、正则、临时集合、匿名对象和大 Bitmap 在热路径中会放大 GC 压力。评审时要关注循环内分配、adapter bind 分配、`remember` 使用位置和对象复用策略。

I/O 和数据库检查是第三类。Room 查询如果缺少索引，开发机上看不出问题，线上大数据用户会出现明显卡顿。N+1 查询也很常见：列表每个 item 单独查收藏状态、库存或用户信息，最终滑动时触发一串数据库或网络请求。评审时要要求批量查询、join、预取或缓存。

图片和资源检查是第四类。`ImageView` 显示 80 dp 缩略图却下载 1080p 图片，或者列表里反复加载同一张圆角图，都会消耗解码、内存和 GPU 资源。评审应检查图片 URL 是否带尺寸参数、是否有占位和错误图、是否限制预加载数量、是否复用 transformation。

## 开发阶段：形成轻量 profiling 习惯

开发阶段的 profiling 不追求完整诊断，只要求尽早发现异常。每个开发者在完成启动任务、核心页面或复杂动画时，应做一次轻量检查：启动路径看一次 System Trace，页面滑动看一次 CPU 和 Memory，布局变化看一次 Layout Inspector，包体积变化看一次 Analyzer。

Android Studio Profiler 适合快速判断“是否有明显主线程长任务”“是否频繁 GC”“是否出现异常 native 分配”。遇到启动或交互问题时，Perfetto / System Trace 更适合看线程、Choreographer、RenderThread、Binder 和 I/O。14.1 中的 Android Studio Profiler 可以作为入口，但不要把 profiler 图上的局部耗时直接当成线上结论。

Layout Inspector 适合检查视图层级、过度绘制和 Compose 重组边界。传统 View 页面要关注层级深度、嵌套 `ConstraintLayout`、透明背景、阴影和无用 wrapper；Compose 页面要关注状态读取范围、`LazyColumn` key、`remember` 位置和不稳定参数导致的重组。

Baseline Profiles 也应在开发期考虑。核心启动和首屏滚动路径一旦确定，就可以补充 profile 生成规则。等到发布前再补 Baseline Profiles，经常会发现路径不稳定、登录态难准备、测试账号不可靠，最终只能覆盖很窄的场景。

## 测试阶段：把性能断言自动化

测试阶段负责把左移实践变成可重复证据。15.6 中的测试最佳实践强调测试条件，性能测试更要控制设备、版本、数据、网络、温度、电量和编译模式。一次跑通没有意义，稳定复现和趋势对比才有价值。

Microbenchmark 适合进入局部热点，例如 JSON 解析、加密签名、图片处理、diff 算法、数据库查询构建和复杂排序。测试要避免测到日志、随机数、网络和文件系统噪声。对 Kotlin 代码，还要注意内联、逃逸分析和对象分配对结果的影响。

Macrobenchmark 适合启动、页面跳转、列表滑动、搜索输入、拍摄预览和结算流程。CI 中跑 Macrobenchmark 时要固定设备池，关闭系统动画，保证测试账号和数据稳定，并保存 trace 文件。指标失败时，开发者应该能从报告跳到 trace，而不是只看到一个红色数字。

Espresso 和 UIAutomator 可以承担简单性能断言。比如核心点击到目标 view 出现不超过 800 ms，输入框输入 20 个字符期间没有明显阻塞，页面滚动后图片数量和网络请求数量符合预期。这些断言不能替代 benchmark，但能防止明显退化进入主干。

## 左移实践的边界

左移不能把所有性能责任前置给开发者。开发者能发现局部风险，但低端机分布、线上灰度、系统 ROM 差异、后端波动和实验干扰仍需要平台能力。比较健康的分工是：设计和代码评审负责预防常见问题；开发自测负责发现明显异常；CI 负责捕捉回归；线上可观测性负责验证真实用户体验。

执行时要避免 checklist 过长。每次评审只保留与改动相关的检查项，并把高频问题自动化。例如主线程 I/O 可以用 StrictMode、lint 或字节码扫描辅助；包体积可以自动统计；启动任务可以要求注册到统一框架。人工评审应该关注架构取舍和边界条件，而不是重复做工具能做的检查。
