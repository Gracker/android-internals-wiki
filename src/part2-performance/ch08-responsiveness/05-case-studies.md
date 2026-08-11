---
title: "案例集"
chapter: "8.5"
section: "8.5"
status: "finalized"
drafted_date: "2026-04-02"
reviewed_date: "2026-05-05"
last_task6_at: 2026-06-16T21:11:00+08:00
rework_date: "2026-05-03"
rework_by: "task2b-rework"
reviewed_by: "openclaw-task6"
review_cycle: 4
re_review_date: "2026-04-09"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-16"
last_verified_against: "Android multidex docs, Android 16KB page size docs, android.os.ProfilingManager / ProfilingTrigger / ProfilingResult docs, AOSP / Perfetto context"
confidence: medium
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
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
task6_result: "pass-light-edit"
last_task6_audit: "2026-07-05"
task9_state: "reviewed"
task2b_state: "fixed"
task2b_result: "fixed"
task9_result: "pass-tech-review"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-06-16"
last_task9_at: "2026-06-16T21:32:37+08:00"
repaired_date: "2026-05-23"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-04-27T19:10:48+08:00"
updated_by: "openclaw-task2b"
updated_date: "2026-05-23"
review_notes: "2026-04-28 task9 deep-review: pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 3 写入 suggestions。；2026-05-03 task9 deep-review: pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 2 写入 suggestions。；2026-05-05 task6 re-review (finalized revisiting): pass-light-edit；L1/L2 轻修并确认 finalized / ready-to-publish。；2026-05-23 task9 re-review: pass-tech-review。AutoFDO 官方指标修复复核通过；无 P0/P1；queue 无 pending（清理 stale pending 1 条），自动晋升 finalized。"
last_task9_audit: "2026-07-09"
last_task9_review_log: "logs/deep-review/2026-06-16-21-deep-review.md"
last_task9_audit_log: "logs/deep-review/2026-07-09-08-audit.md"
task9_review_notes: "2026-05-23 Task9 re-review：pass-tech-review。已复核 16 点抽检 P0（AutoFDO Cold App Launch/Boot/Binder-rpc/Hwbinder 指标）修复；本轮无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-16 13 Task9 idle audit auto-fix：修正 ProfilingManager 触发来源判定 API，`getTag()` 改为 `getTriggerType()` / 文件名 `trigger-type-x`，并补充 `TRIGGER_TYPE_OOM` 返回 Java heap dump 的产物边界；同步 applicable_versions 到 Android 17 / API 37。证据：Android Developers ProfilingTrigger / ProfilingResult / ProfilingManager docs。已回到 Task6 复审。 | 2026-06-16 21 Task9 deep-review：pass-tech-review。ProfilingManager / 16KB / R8 关键 API 复核无 P0/P1；Reddit 绝对耗时与收益拆分作为 P2 数据支撑建议写入 suggestions；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-06-16
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-16
last_task9_autofix_at: "2026-06-16"
---

# 8.5 案例集

下面四个案例用于检验响应时间、启动流程和交互路径的分析方法。资料只采用 Android 官方内容或相关团队发布的一手复盘；二手转述、无法追溯的公司数据和拼接出来的毫秒数不进入结论。

公开资料常只披露相对变化。遇到这种情况，表格把优化前归一化为 1.00，再按报告中的比例换算优化后。例如“耗时降低 20%”记为 1.00 → 0.80。这个数没有秒或毫秒单位，也不代表原报告隐藏了某个绝对值。

阅读案例前要分清几类口径：

- 启动耗时、页面 Time To Interactive（TTI）和点击后的可见反馈，起止点不同。TTID（Time To Initial Display）止于首帧显示，TTFD（Time To Full Display）止于应用声明主要内容已经就绪。
- P50、P90、P95 描述不同分位，不能直接横向比较。
- 实验室 Macrobenchmark、线上 Android vitals 与产品转化率回答的问题不同。
- 一项发布同时带有 R8、Baseline Profiles 或 UI 重写时，只能报告组合结果，除非原团队做过单变量实验。

文中的平台核对上限为 Android 17 / API 37 / android-17.0.0_r1。涉及调度、Binder 或 I/O 归因时，内核对照为 android17-6.18-2026-06_r6。生产案例形成于不同年份，保留历史数据是为了分析优化路径；版本事实以 Android 17 为边界。

---

## 案例一：Reddit 用分屏 CUJ 改善冷启动与页面切换

### 优化前数据

Reddit 没有公开启动耗时的绝对毫秒数。团队在 2024 年发布的案例中说明，他们已经做过多轮性能优化，容易处理的项目基本清完，仍需继续压缩启动、页面加载和滚动开销。团队按屏幕维护性能指标，并结合地域和设备档位观察线上表现。

全局启动指标仍有价值，但单个页面的问题会被总体分布稀释。Reddit 为五条关键用户路径维护 Baseline Profile：

- 首页 Feed 滚动
- 登录
- 全屏视频播放器启动
- subreddit 之间的导航与 Feed 滚动
- 聊天

公开资料没有给出这些路径启用前的绝对值，所以本案例以每项实验自己的基线 1.00 表示优化前。

### 分析过程

团队把“启动后用户会做什么”拆成可执行的 CUJ，由此覆盖三个阶段：进程和首页的冷启动、社区之间的页面加载、页面显示后的滚动帧质量。

这个拆分也改善了归因。首页 Feed、社区 Feed 和登录的代码热度不同，单独生成 Profile 后，某条路径的变化不会被另一条路径的样本量掩盖。团队把 Profile 生成接入 CI，每个版本自动重新生成，减少版本演进造成的规则漂移。

Reddit 同期还启用了 R8 full mode，并升级、重写了部分 Compose UI。官方文章把若干全局指标描述为整个性能计划的结果，不能把每个百分比都算到 Baseline Profile 名下。

### 优化手段

Reddit 的处理包含四项工程动作：

1. 用页面级指标选出高流量 CUJ。
2. 让 Macrobenchmark 执行稳定、可重复的用户操作。
3. 为每条 CUJ 生成 Baseline Profile，并随版本自动更新。
4. 分阶段发布 R8、Profile 和 Compose 改动，观察实验室结果与线上分位是否同向。

Baseline Profile 让 ART 在安装或后台优化阶段优先编译已标记的热点方法，减少关键路径上的解释执行和 JIT 活动。它不会替应用移除 I/O、锁等待或低效布局，页面指标仍要和 Perfetto、帧数据一起看。

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

“首个 Feed Profile 的 51%”与“全局冷启动的 20%”对应特定路径和全局分布，两者口径不同。

### 投入产出比

Reddit 工程师披露，为一个功能团队制作 CUJ Profile 通常只需数小时，约一周后可以观察到生产结果。这个时间只代表单条 CUJ 的协作周期，不含平台团队建设 CI、指标系统和发布实验的初始投入。

可以确认的产出包括冷启动与页面切换分位下降，以及 Profile 随版本重复生成。具体人天成本、服务器费用和每个工具的独立收益没有公开。本地评估应把 Profile 生成、基准设备维护、失败用例修复和发布观察都算入投入。

### 可迁移的做法

首页包含多个入口时，不要只录制“启动到首页”。列表到详情、Tab 切换、搜索结果和深链入口可以各建一条 CUJ，再分别记录 TTID、TTFD、页面 TTI 和帧指标。Profile 覆盖的操作应代表稳定、高频的生产路径；大量低频分支会增加编译成本，也会稀释热点集合。

---

## 案例二：Gmail Wear OS 用 Perfetto 找到 CPU 争用

### 优化前数据

Gmail Wear OS 团队公开了诊断步骤和相对收益，没有披露优化前的毫秒数、设备型号或投入人天。优化前的 Perfetto trace 显示，Wear OS 设备只有两个 CPU，启动期间主线程有较多 Runnable 时间；加载动画、系统工作和应用初始化会争用有限的 CPU 时间。

案例中的 `Android App Startups` 轨道止于首帧，对应 TTID。即使应用调用 `reportFullyDrawn()`，该轨道也不会自动延长到 TTFD。要分析完整内容可用时间，需要在 Perfetto 中单独找到 `reportFullyDrawn()` 标记。

### 分析过程

官方 [Gmail Wear OS 启动案例](https://developer.android.com/topic/performance/appstartup/case-study-gmail-wear) 给出一条可复用的排查顺序：

1. 在 Perfetto 固定 `Android App Startups`、应用主线程状态和主线程 tracepoint。
2. 比较主线程 `Running` 与 `Runnable` 的时间。`Runnable` 表示线程已可运行却暂时没有获得 CPU；占比偏高时继续检查 CPU 争用。
3. 查看 `bindApplication` 附近的 `OpenDexFilesFromOat*`，判断 DEX 读取与代码体积是否占用启动窗口。
4. 沿 `binder transaction` 找到 `system_server` 的 reply 线程，再查看 reply 是否处于 `Runnable (Preempted)`。
5. 检查首帧前后的 JIT 线程。案例中首帧前 JIT 很少，但 `Application creation` 附近仍有后台 JIT 活动，说明 Profile 采集终点可以延长到页面可用状态。

这套步骤把“主线程没在执行”拆成等待 Binder、等待调度、等待 I/O，或被应用自己的动画和工作线程抢占 CPU。只看主线程方法栈无法完整区分这些情况。

### 优化手段

团队做了两组改动，原文分别报告收益：

- 把加载 spinner 换成静态图片，并延后 shimmer 状态，让启动阶段少做持续动画，释放 CPU 给应用主线程和系统服务。
- 启用 R8 对 Baseline Profile 的重写，使代码缩减、重命名后 Profile 仍能对应优化后的程序结构。官方案例注明这项能力要求 AGP 8.2 或更高版本。

延长启动画面不是通用技巧。该案例的作用点是减少双核 Wear OS 设备启动窗口内的动画争用；手机端、不同 UI 状态或无 CPU 争用的 App 应重新测量。为了视觉稳定而无条件延长 Splash，只会增加用户等待。

### 优化后数据

| 实验 | 指标 | 优化前（归一化） | 优化后（归一化） | 原文披露的变化 |
|---|---:|---:|---:|---:|
| 静态加载图 + 延后 shimmer | 启动延迟 | 1.00 | 0.50 | 改善 50% |
| R8 重写 Baseline Profile | 启动延迟 | 1.00 | 0.80 | 改善 20% |

两行来自不同改动。官方资料没有说明它们是否基于同一版本、是否串行叠加，因此不能得出“合计改善 70%”，也不能把 0.50 与 0.80 相乘后写成最终值。

### 投入产出比

团队没有披露工期。从公开范围看，UI 修改和构建配置涉及的代码面较小；采集可对比 trace、维护 Wear OS 设备组合、做 A/B 测试和验证视觉状态仍会消耗工程时间。

这项案例的产出还包括诊断证据：它排除了“主线程方法太多”这一单一解释，并把后续工作指向 DEX、Binder、调度和 JIT 四条可验证路径。资源有限的团队可以借此减少无效重构。

---

## 案例三：Disney+ 清理旧 R8 默认规则

### 优化前数据

Disney+ 的案例没有披露业务规模、DRM 初始化、播放器加载或启动绝对耗时。公开证据只有构建配置和上线后的相对结果，无法补充未发布的启动路径细节。

团队检查 R8 配置时发现，项目使用的默认规则文件带入了 `-dontoptimize`。旧文件 `proguard-android.txt` 包含这条指令，会让 R8 跳过优化步骤。此时即使 release 构建已经开启混淆或缩减，也不能据此推断方法内联、类合并等优化已经生效。

### 分析过程

这个问题涉及五个配置面：

- `isMinifyEnabled` 控制 release 变体是否运行代码缩减与优化流程。
- `isShrinkResources` 控制资源缩减。
- `proguard-android.txt` 是旧默认规则集，其中的 `-dontoptimize` 会关闭代码优化。
- `proguard-android-optimize.txt` 是当前推荐的优化规则入口。
- AGP 8.0 起，R8 full mode 默认开启；历史项目仍可能在 `gradle.properties` 保留 `android.enableR8.fullMode=false`。AGP 9.0 起，官方已经移除对 `proguard-android.txt` 的支持。

文件名、Gradle 属性和 keep rules 要分别检查。只替换文件却保留 fullMode=false，或者使用优化文件后以宽泛 keep 规则保住大量代码，都可能削弱收益。

### 优化手段

Disney+ 将 `proguard-android.txt` 替换为 `proguard-android-optimize.txt`。当前项目照做时还应完成这些验证：

1. 删除历史 compat mode 开关。
2. 在 release 变体开启代码缩减和资源缩减。
3. 以反射、序列化、JNI、动态类加载和依赖注入为重点审查 keep rules。
4. 对优化前后构建运行同一套 Macrobenchmark 和端到端测试。
5. 分阶段发布，并同时观察启动分位、user-perceived ANR、崩溃和功能成功率。

R8 会删除、重命名、移动或合并程序元素。测试只覆盖启动成功还不够，低频反射入口、native 注册和按名称加载的类也要进入回归集。

### 优化后数据

数据来自 Android Developers 发布的 [R8 与 Disney+ 案例](https://developer.android.com/blog/posts/use-r8-to-shrink-optimize-and-fast-track-your-app?hl=en)。

| 指标 | 优化前（归一化） | 优化后（归一化） | 原文披露的变化 |
|---|---:|---:|---:|
| App 启动耗时 | 1.00 | 0.70 | 加快 30% |
| user-perceived ANR | 1.00 | 0.75 | 减少 25% |

第二行是 Google Play 定义的 user-perceived ANR，不能扩写为所有 ANR。原文只说明新版本发布后观察到这两项变化，没有公开 ANR 类型分布，也没有给出每项 R8 优化如何贡献。因果解释应停在配置变更与生产指标同向变化这一层。

### 投入产出比

官方没有披露 Disney+ 的工期和人力，无法给出数值化 ROI。配置改动看起来很小，发布风险却取决于代码库的反射、JNI 和历史 keep rules。大型 App 可能花较多时间清理规则和补齐测试。

评估这类工作时，成本应包含规则审计、自动化测试、灰度发布、崩溃反混淆和回滚准备；产出同时记录启动耗时与 ANR，避免只看包体积。配置迁移后还要在依赖升级时检查新增 consumer rules。

---

## 案例四：Duolingo 缩短点击后的可见等待

### 优化前数据

Duolingo 把性能实验放在三条产品路径上：打开 App、开始一次学习和结束一次学习。团队发布的 [Android 性能复盘](https://blog.duolingo.com/android-app-performance/) 说明，课程结束时要提交本次学习数据，并取回广告、奖励等后续页面。旧流程在这些工作完成前显示全屏加载指示器。

用户点击 `continue` 后能立即获得按压态，但页面主体仍是等待画面。这个案例测量“点击到有意义的完成反馈”的感知等待。公开资料没有披露输入事件到首帧的绝对毫秒数，也没有证明后端请求本身变快。

### 分析过程

团队用 trace marker、系统 trace 和 Perfetto 检查用户路径，重点观察主线程上的两类区间：

- 主线程空闲，但 UI 在等后台 I/O 或网络结果才能继续。
- 主线程长时间执行，导致 frozen frame 或 ANR 风险。

课程结束属于前一类。阻塞条件是“全部后续数据准备完成”，但下一步固定会展示 Session Complete 页面。这提供了一个状态拆分点：本次课程已在本地结束时可以展示完成反馈，数据提交和后续页面准备继续在后台进行。

这种处理要求产品语义允许提前反馈。如果操作涉及不可逆支付、服务器确认或可能失败的安全动作，就不能在成功条件成立前展示“已完成”。即便允许乐观反馈，也要定义重试、离线持久化、失败提示和进程死亡恢复。

### 优化手段

新流程在用户点击 `continue` 后立即展示烟花、动画和 `Session Complete` 文案，同时后台提交数据并准备后续页面。它改变了可见状态的顺序，没有声称缩短整个网络事务。

工程上应把这条路径拆成三个时间点：

- `input_received`：主线程收到点击。
- `meaningful_feedback_drawn`：完成页的有意义反馈已经提交到显示管线。
- `operation_committed`：服务端确认或本地可靠队列完成持久化。

点击响应看前两个时间点；业务完成看第三个。把后两个合成一个指标，会让“反馈快、提交慢”和“反馈慢、提交快”在报表中无法区分。

### 优化后数据

| 指标 | 优化前（归一化） | 优化后（归一化） | 原文披露的变化 |
|---|---:|---:|---:|
| 感知到的 session end 延迟 | 1.00 | 小于等于 0.40 | 降低 60% 以上 |
| 服务端提交耗时 | 未披露 | 未披露 | 不能从案例推断 |
| DAU 与完成 session 数 | 未披露 | 上升 | 原文只给定性结果 |

同一篇复盘还披露整个 2024 Android 性能计划的宏观结果：团队运行 200 多个 A/B 实验；入门设备的 App 打开转化率从 91% 提高到 94.7%；启动等待超过 5 秒的入门设备用户占比从 39% 降到 8%。这些数据属于整个计划，不能归给 session end 这一项改动。

### 投入产出比

Duolingo 没有公开该改动的人天。案例确认感知等待下降 60% 以上，并报告 DAU 与完成 session 数上升，但没有给出这一实验独立贡献的用户数。

ROI 评估要同时检查两面：用户更早看到有意义反馈带来的路径转化；后台任务失败、重试和状态恢复增加的实现成本。只移动动画而不保证业务状态可靠，会把延迟问题换成一致性问题。

### 可迁移的做法

点击后存在不可避免的耗时任务时，先找出用户需要的最早可信反馈。常见选择包括按钮状态变化、已接收提示、本地结果预览或可取消的进行中状态。反馈必须与业务事实一致，并在下一帧内有机会绘制；onClick 内的同步 I/O、锁等待或重计算仍应移出主线程。

---

## 四个案例放在一起怎么看

| 案例 | 覆盖场景 | 主要证据 | 改动位置 | 结果边界 |
|---|---|---|---|---|
| Reddit | 冷启动、页面切换、滚动 | Macrobenchmark、页面级线上指标 | Baseline Profile、R8、UI 演进 | 特定 CUJ 与全局指标分开 |
| Gmail Wear OS | 冷启动 | Perfetto、线程状态、Binder/JIT 轨道 | 加载 UI、Profile 重写 | 两项收益不可相加 |
| Disney+ | 冷启动、ANR | 新旧 release 生产对照 | R8 默认规则 | 无绝对耗时与工期 |
| Duolingo | 点击响应 | trace、A/B 测试、产品转化 | 反馈状态与后台任务顺序 | 感知延迟不等于事务耗时 |

这些案例没有给出适用于所有 App 的固定优先级。它们共同支持一种证据顺序：定义用户路径和时间边界，用 trace 判断 CPU、调度、I/O、Binder、编译或绘制中的瓶颈，做尽量单一的改动，再在相同口径下比较前后版本。

### 实验记录模板

每次响应速度优化至少记录这些字段：

| 字段 | 要回答的问题 |
|---|---|
| CUJ | 用户从哪个动作开始，到哪个可见或可交互状态结束？ |
| 指标定义 | TTID、TTFD、页面 TTI、点击到反馈或事务完成中的哪一个？ |
| 样本 | 设备档位、系统版本、刷新率、温度、网络与登录状态是否一致？ |
| 基线 | 优化前的 P50、P90、P95、样本量和构建版本是什么？ |
| Trace 证据 | 时间消耗位于 Running、Runnable、Sleep、Binder、I/O、JIT 还是帧管线？ |
| 变量 | 改了哪些内容，能否和其他变更隔离？ |
| 结果 | 实验室与线上指标是否同向，置信区间和异常样本如何？ |
| 成本 | 开发、测试、CI、设备、发布观察和维护分别花了多少？ |
| 风险 | 功能成功率、崩溃、ANR、功耗、内存和数据一致性是否回退？ |
| 守门 | 采用什么阈值阻止后续版本回退？ |

Macrobenchmark 适合建立可重复的启动和交互基准，[官方概览](https://developer.android.com/topic/performance/benchmarking/macrobenchmark-overview) 说明可测的启动、帧和自定义 trace 指标。生产分布还应结合 Android vitals 与应用自己的 CUJ 指标；实验室的一台高速设备不能代替真实设备分层。

### 投入产出比的计算边界

没有金额和人天时，不写“高 ROI”作为结论。可以报告三组可审计信息：

- 一次性成本：实现、测试、基准设施、灰度与回滚。
- 持续成本：Profile 更新、设备实验室、告警维护和规则审计。
- 产出：耗时分位、慢帧、ANR、转化率、留存或支持工单的变化。

同一项收益不要重复计入。例如启动变快可能同时改善转化率，两者可以并列展示，却不能在没有经济模型时相加成一个虚构金额。某项案例只给相对变化时，本地团队仍需用自己的样本量和用户价值计算是否值得投入。

---

## Android 17 锚点下的归因边界

四个案例以 App 和构建工具为主，不依赖某个 Android 17 新 API。迁移到当前平台时，仍要使用统一锚点解释 trace：

- 平台源码对照 android-17.0.0_r1，API 上限 37。
- 内核调度、唤醒、页缓存与 Binder 驱动对照 android17-6.18-2026-06_r6。
- 主线程处于 Running 时，优先检查应用或 framework 正在执行的代码。
- 主线程处于 Runnable 时，继续检查 CPU 争用、线程优先级与调度；不能把 Runnable 直接写成“CPU 不够”。
- Binder 调用耗时时，沿 transaction/reply 查看服务端线程和调度状态；调用端切片长不等于 system_server 执行慢。
- I/O 或缺页占主导时，要区分冷缓存、设备存储和内核版本，避免把一台设备的收益外推到全量用户。

Android 17 的 framework 或 6.18 内核可能改变某些切片的成本，案例中的历史百分比不能当成平台承诺。迁移时复用诊断步骤，在当前基线重新采集数据。

---

## 常见误读

### 把归一化值当成毫秒

1.00 → 0.70 只表示相对耗时降低 30%。原报告没有绝对值时，无法据此计算“节省了多少毫秒”，也无法判断优化后是否达到产品目标。

### 把多个百分比相加

同一团队可能在不同版本、设备和指标上报告多项变化。没有实验设计说明时，51% 与 20%、50% 与 20% 都不能相加。串行实验还会受到基线变化和交互效应影响。

### 用启动首帧代替可交互

TTID 只说明首帧已经显示。页面数据、控件可用性和必需状态仍可能没有完成。应为 TTFD 或页面 TTI 设置独立标记，并写清 `reportFullyDrawn()` 的调用条件。

### 用点击回调结束代替用户反馈

`onClick` 返回只说明回调结束，不说明新状态已经显示。点击响应指标至少应延伸到有意义帧呈现；需要服务端确认的操作还要保留事务完成指标。

### 根据配置名猜测 R8 已优化

启用 minify、选择默认规则文件、full mode 属性和 keep rules 会共同影响结果。要检查 release 产物、测试行为与基准数据，不能依据一个布尔值或文件名下结论。

### 把生产相关性写成代码机制证明

生产版本上线后启动与 ANR 同向改善，可以支持“这次发布有效”，却不足以证明某个内联或类合并直接减少了某类 ANR。机制结论需要 trace、消融实验或更细的错误分类。

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
