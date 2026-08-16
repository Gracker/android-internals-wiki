---
title: "案例集"
chapter: "8.5"
section: "8.5"
status: "finalized"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-16"
last_verified_against: "Android multidex docs, Android 16KB page size docs, android.os.ProfilingManager / ProfilingTrigger / ProfilingResult docs, AOSP / Perfetto context"
confidence: medium
sources:
  - type: blog
    path: "性能优化日报/2026-03-31-性能优化日报.md (Reddit R8 full mode)"
  - type: blog
    path: "性能优化日报/2026-03-13-大厂-抖音启动优化实践2025.md"
  - type: official
    path: "developer.android.com/topic/performance/baselineprofiles"
  - type: blog
    path: "性能优化日报/2026-03-14-官方 社区-Android Baseline Profiles 启动优化实战.md"
  - type: official
    path: "android-developers.googleblog.com (Google AutoFDO)"
  - type: official
    path: "https://developer.android.com/reference/android/os/ProfilingManager"
  - type: blog
    path: "性能优化日报/2026-03-15-Baseline-Profiles-启动优化标配.md"
tags: ['case-study', 'cold-start', 'response-optimization', 'baseline-profile', 'r8-full-mode', 'page-switch', 'macrobenchmark', 'auto-fdo', '16kb-page', 'dag-scheduler', 'aot-compilation']
related_chapters: ["8.1", "8.2", "8.3", "8.4", "3.2"]
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task2b_state: "fixed"
---

# 8.5 案例集

下面四个案例用于检验前文分析响应时间、启动流程和交互路径的方法。资料只采用 Android 官方内容或相关团队发布的一手复盘；二手转述、来源无法追溯的公司数据，以及根据零散信息拼出的毫秒数都不进入结论。

公开资料经常只披露相对变化。遇到这种情况，表格会把优化前的数值归一化为 1.00，再按照报告中的比例换算优化后数值。例如，“耗时降低 20%”记为 1.00 → 0.80。归一化值没有秒或毫秒单位，也不表示原报告中存在未公开的绝对值。

阅读案例前要分清几类口径：

- 启动耗时、页面 Time to Interactive（TTI，可交互时间）和点击后的可见反馈使用不同的起止点。TTID（Time to Initial Display）止于首帧显示，TTFD（Time to Full Display）止于应用声明主要内容已经就绪。
- P50、P90、P95 表示第 50、90、95 百分位，不能直接横向比较。
- 实验室 Macrobenchmark、线上 Android Vitals 和产品转化率回答的问题不同。
- 一项发布同时带有 R8、Baseline Profiles 或 UI 重写时，只能报告组合结果，除非原团队做过单变量实验。

本文核对的平台上限为 Android 17 / API 37，源码基线是 `android-17.0.0_r1`。涉及调度、Binder 或 I/O 归因时，内核基线为 `android17-6.18-2026-06_r6`。这些生产案例形成于不同年份，保留历史数据是为了分析优化方法；平台版本事实仍以 Android 17 为边界。

---

## 案例一：Reddit 用分屏 CUJ 改善冷启动与页面切换

### 优化前数据

CUJ（Critical User Journey，关键用户旅程）是一条可以重复执行和测量的典型用户操作路径。Reddit 没有公开启动耗时的绝对毫秒数。团队在 2024 年发布的案例中说明，他们已经进行过多轮性能优化，容易处理的问题大多已经解决，仍需继续降低启动、页面加载和滚动开销。团队按页面维护性能指标，并结合地域和设备档位观察线上表现。

全局启动指标仍有价值，但单个页面的问题可能被总体分布掩盖。Reddit 为五条高频用户路径维护 Baseline Profile：

- 首页 Feed 滚动
- 登录
- 全屏视频播放器启动
- subreddit 之间的导航与 Feed 滚动
- 聊天

公开资料没有给出这些路径启用前的绝对值，因此本案例使用每项实验自己的基线 1.00 表示优化前状态。

### 分析过程

团队将“启动后用户会做什么”定义成可执行的 CUJ，从而覆盖三个阶段：进程和首页的冷启动、社区之间的页面加载，以及页面显示后的滚动帧质量。

这种划分也让归因更明确。首页 Feed、社区 Feed 和登录路径执行的热点代码不同；分别生成 Profile 后，某条路径的变化不会被另一条路径的大量样本掩盖。团队还将 Profile 生成接入 CI，为每个版本自动重新生成，减少代码演进后规则与真实路径不再匹配的问题。

Reddit 同期还启用了 R8 full mode（完整优化模式），并升级、重写了部分 Compose UI。官方文章将若干全局指标归为整个性能计划的结果，因此不能把每个百分比都算作 Baseline Profile 的独立收益。

### 优化手段

Reddit 进行了四项工程改动：

1. 用页面级指标选出高流量 CUJ。
2. 让 Macrobenchmark 执行稳定、可重复的用户操作。
3. 为每条 CUJ 生成 Baseline Profile，并随版本自动更新。
4. 分阶段发布 R8、Profile 和 Compose 改动，观察实验室结果和线上分位数是否同向变化。

Baseline Profile 让 ART 在安装或后台优化阶段优先编译已标记的热点方法，从而减少关键路径上的解释执行和 JIT（运行时即时编译）。它不会替应用移除 I/O、锁等待或低效布局，因此页面指标仍要结合 Perfetto 和帧数据分析。

### 优化后数据

以下数字均来自 Reddit 与 Android Developers 联合发布的 [2024 年案例](https://android-developers.googleblog.com/2024/12/reddit-improved-app-startup-speed-using-baseline-profiles-r8.html)。

| 范围 | 指标 | 优化前（归一化） | 优化后（归一化） | 原文披露的变化 | 归因边界 |
|---|---:|---:|---:|---:|---|
| 首个 Feed Profile 的早期基准 | 启动耗时中位数 | 1.00 | 0.49 | 降低 51% | 原文归到该 Baseline Profile |
| 首页 Feed | P95 frozen frames | 1.00 | 0.64 | 降低 36% | 原文归到首页 Feed Profile |
| 社区 Feed | P90 TTI | 1.00 | 0.88 | 改善 12% | 原文归到社区 Feed Profile |
| 社区 Feed | 首帧时间 | 1.00 | 0.78 | 降低 22% | 原文归到社区 Feed Profile |
| 社区 Feed | P90 slow frames | 1.00 | 0.88 | 降低 12% | 原文归到社区 Feed Profile |
| App 全局 | 冷启动 | 1.00 | 0.80 | 改善 20% | Profile、R8 与 UI 演进的整体结果 |

“首个 Feed Profile 的 51%”描述特定路径，“全局冷启动的 20%”描述整体分布，两者口径不同。

### 投入产出比

Reddit 工程师披露，一个功能团队制作一条 CUJ Profile 通常只需数小时，约一周后可以观察到生产结果。这段时间只代表单条 CUJ 的协作周期，不包括平台团队搭建 CI、指标系统和发布实验的初始投入。

可以确认的产出包括冷启动与页面切换分位数下降，以及 Profile 能随版本重复生成。原文没有公开具体人天成本、服务器费用和每项工具的独立收益。本地评估时，应把 Profile 生成、基准设备维护、失败用例修复和发布观察都计入投入。

### 可迁移的做法

首页包含多个入口时，不应只录制“启动到首页”。列表到详情、Tab 切换、搜索结果和深链入口可以分别建立 CUJ，再记录各自的 TTID、TTFD、页面 TTI 和帧指标。Profile 覆盖的操作应代表稳定、高频的真实用户路径；纳入大量低频分支会增加编译成本，也会降低热点集合的集中度。

---

## 案例二：Gmail Wear OS 用 Perfetto 找到 CPU 争用

### 优化前数据

Gmail Wear OS 团队公开了诊断步骤和相对收益，但没有披露优化前的毫秒数、设备型号或投入人天。优化前的 Perfetto trace 显示，测试使用的 Wear OS 设备只有两个 CPU，启动期间主线程有较多 Runnable 时间；这表示线程已经可以运行，却暂时没有获得 CPU。加载动画、系统工作和应用初始化会争用有限的 CPU 时间。

案例中的 `Android App Startups` 轨道止于首帧，对应 TTID。即使应用调用了 `reportFullyDrawn()`，这条轨道也不会自动延长到 TTFD。分析完整内容可用时间时，需要在 Perfetto 中另外找到 `reportFullyDrawn()` 标记。

### 分析过程

官方 [Gmail Wear OS 启动案例](https://developer.android.com/topic/performance/appstartup/case-study-gmail-wear) 给出一条可复用的排查顺序：

1. 在 Perfetto 中固定显示 `Android App Startups`、应用主线程状态和主线程 tracepoint（代码埋入的跟踪点）。
2. 比较主线程 `Running` 与 `Runnable` 的时间。`Runnable` 表示线程已可运行却暂时没有获得 CPU；占比偏高时继续检查 CPU 争用。
3. 查看 `bindApplication` 附近的 `OpenDexFilesFromOat*`，判断读取 OAT / DEX 和代码体积是否占用了启动时间窗口。
4. 沿 `binder transaction` 找到 `system_server` 的 reply（回复）线程，再查看它是否处于 `Runnable (Preempted)`，也就是可运行但刚被其他线程抢占。
5. 检查首帧前后的 JIT 线程。案例中首帧前的 JIT 很少，但 `Application creation` 附近仍有后台 JIT 活动，说明 Profile 的录制范围可以延伸到页面达到可用状态。

这套步骤进一步判断“主线程没有执行”的原因究竟是等待 Binder、等待调度、等待 I/O，还是 CPU 被应用自己的动画和工作线程占用。只查看主线程方法栈，无法完整区分这些情况。

### 优化手段

团队做了两组改动，原文分别报告收益：

- 将加载 spinner（旋转指示器）换成静态图片，并推迟 shimmer（扫光动画）状态，让启动阶段减少持续动画，把更多 CPU 时间留给应用主线程和系统服务。
- 启用 R8 对 Baseline Profile 的重写，使代码缩减、重命名后 Profile 仍能对应优化后的程序结构。官方案例注明这项能力要求 AGP 8.2 或更高版本。

延长启动画面不是通用优化手段。这个案例减少的是双核 Wear OS 设备启动期间的动画争用；手机、不同 UI 状态或没有 CPU 争用的应用都应重新测量。为了视觉稳定而无条件延长 Splash，只会增加用户等待时间。

### 优化后数据

| 实验 | 指标 | 优化前（归一化） | 优化后（归一化） | 原文披露的变化 |
|---|---:|---:|---:|---:|
| 静态加载图 + 延后 shimmer | 启动延迟 | 1.00 | 0.50 | 改善 50% |
| R8 重写 Baseline Profile | 启动延迟 | 1.00 | 0.80 | 改善 20% |

两行来自不同改动。官方资料没有说明它们是否基于同一版本、是否串行叠加，因此不能得出“合计改善 70%”，也不能把 0.50 与 0.80 相乘后写成最终值。

### 投入产出比

团队没有披露工期。从公开信息看，UI 修改和构建配置涉及的代码范围较小；但采集可比较的 trace、维护 Wear OS 设备组合、执行 A/B 测试和验证视觉状态仍需要工程投入。

这个案例的产出还包括一套诊断证据：它排除了“主线程执行的方法太多”这一单一解释，并将后续工作指向 DEX、Binder、调度和 JIT 四条可验证路径。资源有限的团队可以借此减少没有证据支持的重构。

---

## 案例三：Disney+ 清理旧 R8 默认规则

### 优化前数据

Disney+ 的案例没有披露业务规模、DRM 初始化、播放器加载或启动绝对耗时。公开证据只有构建配置和上线后的相对结果，不能据此补充未发布的启动路径细节。

团队检查 R8 配置时发现，项目使用的默认规则文件带入了 `-dontoptimize`。旧文件 `proguard-android.txt` 包含这条指令，会让 R8 跳过代码优化步骤。因此，即使 release 构建已经开启重命名或代码缩减，也不能据此判断方法内联、类合并等优化已经生效。

### 分析过程

这个问题涉及五个配置面：

- `isMinifyEnabled` 控制 release 变体是否运行代码缩减和优化流程。
- `isShrinkResources` 控制资源缩减。
- `proguard-android.txt` 是旧默认规则集，其中的 `-dontoptimize` 会关闭代码优化。
- `proguard-android-optimize.txt` 是当前推荐的优化规则入口。
- 从 AGP 8.0 开始，R8 full mode 默认开启；历史项目仍可能在 `gradle.properties` 中保留 `android.enableR8.fullMode=false`。从 AGP 9.0 开始，官方已经移除对 `proguard-android.txt` 的支持。

文件名、Gradle 属性和 keep rules（保留规则）需要分别检查。只替换规则文件却保留 `fullMode=false`，或者使用优化文件后又通过宽泛的 keep rules 保留大量代码，都会削弱收益。

### 优化手段

Disney+ 将 `proguard-android.txt` 替换为 `proguard-android-optimize.txt`。当前项目照做时还应完成这些验证：

1. 删除历史 compat mode 开关。
2. 在 release 变体开启代码缩减和资源缩减。
3. 重点检查反射、序列化、JNI、动态类加载和依赖注入相关的 keep rules。
4. 对优化前后构建运行同一套 Macrobenchmark 和端到端测试。
5. 分阶段发布，并同时观察启动分位、user-perceived ANR、崩溃和功能成功率。

R8 会删除、重命名、移动或合并程序元素。测试只覆盖应用能否启动还不够，低频反射入口、native 注册和按名称加载的类也要纳入回归测试。

### 优化后数据

数据来自 Android Developers 发布的 [R8 与 Disney+ 案例](https://developer.android.com/blog/posts/use-r8-to-shrink-optimize-and-fast-track-your-app?hl=en)。

| 指标 | 优化前（归一化） | 优化后（归一化） | 原文披露的变化 |
|---|---:|---:|---:|
| App 启动耗时 | 1.00 | 0.70 | 加快 30% |
| user-perceived ANR | 1.00 | 0.75 | 减少 25% |

第二行是 Google Play 定义的 user-perceived ANR（用户感知到的 ANR），不能扩展成所有 ANR。原文只说明新版本发布后观察到这两项变化，没有公开 ANR 类型分布，也没有给出各项 R8 优化分别贡献了多少。现有证据只能支持配置变更与生产指标同向变化。

### 投入产出比

官方没有披露 Disney+ 的工期和人力，无法计算数值化 ROI（投资回报率）。配置改动看起来很小，发布风险却取决于代码库中的反射、JNI 和历史 keep rules。大型应用可能需要投入较多时间清理规则并补齐测试。

评估这类工作时，成本应包括规则检查、自动化测试、灰度发布、崩溃反混淆和回滚准备；产出应同时记录启动耗时和 ANR，不能只看包体积。完成配置迁移后，依赖升级时还要检查新增的 consumer rules（库随包提供的消费者规则）。

---

## 案例四：Duolingo 缩短点击后的可见等待

### 优化前数据

Duolingo 围绕三条产品路径开展性能实验：打开应用、开始一次学习和结束一次学习。团队发布的 [Android 性能复盘](https://blog.duolingo.com/android-app-performance/) 说明，课程结束时需要提交本次学习数据，并获取广告、奖励等后续页面信息。旧流程在所有这些工作完成前一直显示全屏加载指示器。

用户点击 `continue` 后能立即看到按钮按下状态，但页面主体仍然是等待画面。这个案例测量的是从点击到出现有意义完成反馈的感知等待。公开资料没有披露输入事件到首帧的绝对毫秒数，也没有证明后端请求本身变快。

### 分析过程

团队使用 trace marker（自定义跟踪标记）、系统 trace 和 Perfetto 检查用户路径，重点观察两类区间：

- 主线程空闲，但 UI 必须等待后台 I/O 或网络结果才能继续。
- 主线程长时间执行，导致 frozen frame 或 ANR 风险。

课程结束属于第一类。旧流程的继续条件是“全部后续数据都已准备完成”，但下一步固定会展示 Session Complete 页面。因此可以把状态分为两步：课程在本地结束后立即显示完成反馈，数据提交和后续页面准备继续在后台进行。

这种处理要求产品语义允许提前反馈。如果操作涉及不可逆支付、必须等待服务器确认，或可能失败的安全动作，就不能在成功条件成立前显示“已完成”。即使允许 optimistic feedback（基于本地状态提前反馈），也要定义重试、离线持久化、失败提示和进程死亡后的恢复方式。

### 优化手段

新流程在用户点击 `continue` 后立即显示烟花、动画和 `Session Complete` 文案，同时在后台提交数据并准备后续页面。它改变的是可见状态的先后顺序，并未声称整个网络事务变得更快。

工程上可以为这条路径记录三个时间点：

- `input_received`：主线程收到点击。
- `meaningful_feedback_drawn`：完成页的有意义反馈已经提交到显示管线。
- `operation_committed`：服务端确认或本地可靠队列完成持久化。

点击响应由前两个时间点决定，业务完成由第三个时间点决定。如果把后两个时间点合为一个指标，报表就无法区分“反馈快、提交慢”和“反馈慢、提交快”。

### 优化后数据

| 指标 | 优化前（归一化） | 优化后（归一化） | 原文披露的变化 |
|---|---:|---:|---:|
| 感知到的 session end 延迟 | 1.00 | 小于等于 0.40 | 降低 60% 以上 |
| 服务端提交耗时 | 未披露 | 未披露 | 不能从案例推断 |
| DAU 与完成 session 数 | 未披露 | 上升 | 原文只给定性结果 |

同一篇复盘还披露了整个 2024 Android 性能计划的总体结果：团队运行了 200 多个 A/B 实验；入门设备的应用打开转化率从 91% 提高到 94.7%；启动等待超过 5 秒的入门设备用户占比从 39% 降到 8%。这些数据属于整个计划，不能归因于 session end 这一项改动。

### 投入产出比

Duolingo 没有公开这项改动投入的人天。案例确认感知等待下降 60% 以上，并报告 DAU（日活跃用户数）和完成 session 数上升，但没有给出这项实验独立贡献的用户数。

评估 ROI 时要同时检查两方面：用户更早看到有意义反馈后，路径转化率如何变化；为后台任务失败、重试和状态恢复新增了多少实现成本。只移动动画而不保证业务状态可靠，会让延迟问题转变为数据一致性问题。

### 可迁移的做法

点击后存在无法避免的耗时任务时，应先找出用户能够看到的最早可信反馈。常见选择包括按钮状态变化、操作已接收提示、本地结果预览或可取消的进行中状态。反馈必须符合当前业务事实，并且有机会在下一帧绘制；`onClick` 中的同步 I/O、锁等待或大量计算仍应移出主线程。

---

## 四个案例放在一起怎么看

| 案例 | 覆盖场景 | 主要证据 | 改动位置 | 结果边界 |
|---|---|---|---|---|
| Reddit | 冷启动、页面切换、滚动 | Macrobenchmark、页面级线上指标 | Baseline Profile、R8、UI 演进 | 特定 CUJ 与全局指标分开 |
| Gmail Wear OS | 冷启动 | Perfetto、线程状态、Binder/JIT 轨道 | 加载 UI、Profile 重写 | 两项收益不可相加 |
| Disney+ | 冷启动、ANR | 新旧 release 生产对照 | R8 默认规则 | 无绝对耗时与工期 |
| Duolingo | 点击响应 | trace、A/B 测试、产品转化 | 反馈状态与后台任务顺序 | 感知延迟不等于事务耗时 |

这些案例没有给出适用于所有应用的固定优化顺序，但都采用了相似的证据流程：先定义用户路径和时间边界，再用 trace 判断瓶颈位于 CPU、调度、I/O、Binder、编译还是绘制，尽量一次只改变一个因素，最后按相同口径比较前后版本。

### 实验记录模板

每次响应速度优化至少记录这些字段：

| 字段 | 要回答的问题 |
|---|---|
| CUJ | 用户从哪个动作开始，到哪个可见或可交互状态结束？ |
| 指标定义 | TTID、TTFD、页面 TTI、点击到反馈或事务完成中的哪一个？ |
| 样本 | 设备档位、系统版本、刷新率、温度、网络与登录状态是否一致？ |
| 基线 | 优化前的 P50、P90、P95、样本量和构建版本是什么？ |
| Trace 证据 | 时间花在 Running、Runnable、Sleep、Binder、I/O、JIT 还是帧处理路径？ |
| 变量 | 改了哪些内容，能否和其他变更隔离？ |
| 结果 | 实验室与线上指标是否同向，置信区间和异常样本如何？ |
| 成本 | 开发、测试、CI、设备、发布观察和维护分别花了多少？ |
| 风险 | 功能成功率、崩溃、ANR、功耗、内存和数据一致性是否回退？ |
| 守门 | 使用什么阈值阻止后续版本出现性能回退？ |

Macrobenchmark 适合建立可重复的启动和交互基准，[官方概览](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview) 说明了可测量的启动、帧和自定义 trace 指标。生产分布还应结合 Android Vitals 和应用自己的 CUJ 指标；实验室中的一台高性能设备无法代表真实用户的设备分层。

### 投入产出比的计算边界

没有金额和人天数据时，不应把“高 ROI”写成结论。可以报告三组能够复核的信息：

- 一次性成本：实现、测试、基准设施、灰度发布和回滚。
- 持续成本：Profile 更新、设备实验室、告警维护和规则审计。
- 产出：耗时分位、慢帧、ANR、转化率、留存或支持工单的变化。

同一项收益不能重复计入。例如，启动变快可能同时改善转化率，两者可以并列展示，但在没有经济模型时不能相加成一个虚构金额。案例只提供相对变化时，本地团队仍需根据自己的样本量和用户价值判断是否值得投入。

---

## Android 17 锚点下的归因边界

四个案例主要涉及应用代码和构建工具，不依赖某个 Android 17 新 API。将方法迁移到当前平台时，仍要使用统一基线解释 trace：

- 平台源码对照 `android-17.0.0_r1`，API 上限为 37。
- 内核调度、唤醒、页缓存和 Binder 驱动对照 `android17-6.18-2026-06_r6`。
- 主线程处于 Running 时，优先检查应用或 framework 正在执行的代码。
- 主线程处于 Runnable 时，继续检查 CPU 争用、线程优先级和调度；不能把 Runnable 直接写成“CPU 不够”。
- Binder 调用耗时时，沿 transaction/reply 查看服务端线程和调度状态；调用端切片长不等于 system_server 执行慢。
- I/O 或缺页占主要时间时，要区分冷缓存、设备存储和内核版本，避免把一台设备上的收益外推到全部用户。

Android 17 framework 或 6.18 内核可能改变某些 slice 的耗时，案例中的历史百分比不能当成平台承诺。迁移时可以复用诊断步骤，但必须在当前基线上重新采集数据。

---

## 常见误读

### 把归一化值当成毫秒

1.00 → 0.70 只表示相对耗时降低 30%。原报告没有提供绝对值时，无法据此计算节省了多少毫秒，也无法判断优化后是否达到了产品目标。

### 把多个百分比相加

同一团队可能针对不同版本、设备和指标报告多项变化。没有实验设计说明时，51% 与 20%、50% 与 20% 都不能相加。按顺序进行的多次实验还会受到基线变化和交互效应影响，后者表示一项改动可能改变另一项改动的收益。

### 用启动首帧代替可交互

TTID 只能说明首帧已经显示，页面数据、控件可用性和必需状态仍可能没有准备完成。应为 TTFD 或页面 TTI 设置独立标记，并写清 `reportFullyDrawn()` 的调用条件。

### 用点击回调结束代替用户反馈

`onClick` 返回只说明回调已经结束，不说明新状态已经显示。点击响应指标至少应延伸到包含有意义反馈的帧呈现；需要服务端确认的操作还要单独保留事务完成指标。

### 根据配置名猜测 R8 已优化

minify 开关、默认规则文件、full mode 属性和 keep rules 会共同影响结果。要检查 release 产物、测试行为和基准数据，不能只依据一个布尔值或文件名下结论。

### 把生产相关性写成代码机制证明

生产版本上线后，启动和 ANR 指标同向改善，可以支持“这次发布有效”，但不足以证明某个方法内联或类合并直接减少了某类 ANR。要证明具体机制，还需要 trace、消融实验，或更细的错误分类；消融实验是指只移除或保留某一项改动，观察结果如何变化。

---

## 参考资料

- [Reddit：Baseline Profiles、R8 与 Compose 的生产案例](https://android-developers.googleblog.com/2024/12/reddit-improved-app-startup-speed-using-baseline-profiles-r8.html)
- [Reddit：R8、Baseline Profiles 与 Startup Profiles 的后续基准](https://developer.android.com/blog/posts/how-reddit-used-the-r8-optimizer-for-high-impact-performance-improvements?hl=en)
- [Gmail Wear OS：用 Perfetto 分析启动并改善 50%](https://developer.android.com/topic/performance/appstartup/case-study-gmail-wear)
- [Disney+：清理旧 R8 默认规则后的生产结果](https://developer.android.com/blog/posts/use-r8-to-shrink-optimize-and-fast-track-your-app?hl=en)
- [Duolingo：Android 性能实验与点击后感知等待案例](https://blog.duolingo.com/android-app-performance/)
- [Baseline Profiles 官方概览](https://developer.android.com/topic/performance/baselineprofiles/overview)
- [R8 full mode 官方说明](https://developer.android.com/topic/performance/app-optimization/full-mode?hl=en)
- [启用 App 优化的官方指南](https://developer.android.com/topic/performance/app-optimization/enable-app-optimization)
- [Macrobenchmark 官方概览](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview)
- [Android App 性能度量概览](https://developer.android.com/topic/performance/measuring-performance)
