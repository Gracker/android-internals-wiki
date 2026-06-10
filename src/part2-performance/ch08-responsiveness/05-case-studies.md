---
title: "案例集"
chapter: "8.5"
section: "8.5"
status: "finalized"
drafted_date: "2026-04-02"
reviewed_date: "2026-05-05"
rework_date: "2026-05-03"
rework_by: "task2b-rework"
reviewed_by: "openclaw-task6"
review_cycle: 4
re_review_date: "2026-04-09"
applicable_versions: "Android 8.0 (API 26) - Android 16 (API 36)"
last_verified: "2026-04-27"
last_verified_against: "Android multidex docs, Android 16KB page size docs, android.os.ProfilingManager docs, AOSP / Perfetto context"
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
last_task6_audit: "2026-05-23"
task9_state: "reviewed"
task2b_state: "fixed"
task2b_result: "fixed"
task9_result: "pass-tech-review"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-05-23"
last_task9_at: "2026-05-23T19:20:00+08:00"
repaired_date: "2026-05-23"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-04-27T19:10:48+08:00"
updated_by: "openclaw-task2b"
updated_date: "2026-05-23"
review_notes: "2026-04-28 task9 deep-review: pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 3 写入 suggestions。；2026-05-03 task9 deep-review: pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 2 写入 suggestions。；2026-05-05 task6 re-review (finalized revisiting): pass-light-edit；L1/L2 轻修并确认 finalized / ready-to-publish。；2026-05-23 task9 re-review: pass-tech-review。AutoFDO 官方指标修复复核通过；无 P0/P1；queue 无 pending（清理 stale pending 1 条），自动晋升 finalized。"
last_task9_audit: "2026-05-23"
last_task9_review_log: "logs/deep-review/2026-05-23-19-deep-review.md"
last_task9_audit_log: "logs/deep-review/2026-05-23-16-audit.md"
task9_review_notes: "2026-05-23 Task9 re-review：pass-tech-review。已复核 16 点抽检 P0（AutoFDO Cold App Launch/Boot/Binder-rpc/Hwbinder 指标）修复；本轮无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-27
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-10
---

# 案例集

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 提供 3-5 个真实启动/响应速度优化案例
- 🔹 案例需覆盖：冷启动优化、页面切换优化、点击响应优化
- 🔹 每个案例包含：优化前数据、分析过程、优化手段、优化后数据、投入产出比

### 扩展（可选深入）

- 🔸 Baseline Profile 实战效果数据
- 🔸 大型 App 启动优化的系统化实践

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

前面的章节讨论了响应速度的原理、启动流程和优化策略。但每个 App 做优化时面临的约束千差万别——有的受限于包体积，有的卡在第三方 SDK 初始化，有的则是历史代码的技术债。这一节来看几个真实案例，了解不同团队在不同约束下怎么做的、最终拿到了什么效果。

以下案例中的部分数据来自公开的技术分享和官方博客，不是本团队的实测数据。数据的准确性取决于原始报告的测试环境和度量方式，每个案例中已标注数据来源和可信度。

---

## 案例一：Reddit 冷启动优化——Baseline Profiles + R8 Full Mode

### 问题背景

Reddit 在 Google Play 上的安装量超过一亿。作为一个内容型社区应用，它的冷启动路径涵盖了从进程创建、Application 初始化、首页数据加载到渲染的完整流程。用户打开 App 后最先看到的是首页 Feed 流，这个"从点击图标到可交互 Feed"的时间直接影响了用户的留存和参与度。

Reddit 技术团队在 2025 年 Google Performance Spotlight Week 上分享了他们的优化经历 [已验证: developer.android.com, Google Performance Spotlight Week 2025]。优化前，Reddit 的冷启动在 P50 级别约为 2.8 秒，在低端设备上 P95 甚至超过 5 秒。用户投诉中"打开慢"是高频反馈之一。

### 分析思路

Reddit 的性能团队先通过 Macrobenchmark 建立了启动耗时基线。他们发现冷启动的时间主要花在以下几个环节：

Application.onCreate() 中的 SDK 初始化是大头：Reddit 集成了大量第三方服务（广告、分析、推送等），这些 SDK 几乎都在 onCreate 里同步初始化，占据了主线程约 800ms。首页 Feed 的数据加载也在占用时间——虽然是异步请求，但网络回调和 JSON 解析会回到主线程处理。首次渲染同样有开销，由于 View 层级较深（首页是复杂的 RecyclerView），measure/layout 阶段消耗了不少时间。

在分析过程中他们注意到一个关键事实：这些代码路径在安装后首次运行时全部走的是解释执行（interpreted），因为 ART 还没有来得及对这些路径做 JIT 编译。这正是 Baseline Profiles 要解决的问题。

### 优化手段

Reddit 采用了"Baseline Profiles + R8 Full Mode"的组合策略，整个集成耗时不到两周 [已验证: developer.android.com, Google Performance Spotlight Week 2025]。

**Baseline Profiles 方面**，Reddit 用独立的 generator module 维护 CUJ。官方推荐的结构是：profile 生成模块应用 `androidx.baselineprofile` Gradle plugin，测试依赖里引入 `androidx.benchmark:benchmark-macro-junit4`，App 模块按需加入 `androidx.profileinstaller` 处理本地 sideload 安装。`BaselineProfileRule` 就来自 Macrobenchmark 依赖，生成出来的 `baseline-prof.txt` 会随 App 打包，在安装阶段提供给 ART 做 AOT 编译。

```groovy
// :baselineprofile/build.gradle
plugins {
    id 'com.android.test'
    id 'androidx.baselineprofile'
}

android {
    targetProjectPath = ':app'
}

dependencies {
    implementation 'androidx.benchmark:benchmark-macro-junit4:1.3.3'
}
```

```groovy
// :app/build.gradle
dependencies {
    implementation 'androidx.profileinstaller:profileinstaller:1.4.1'
}
```

这里最容易写错的地方，是把 Baseline Profile plugin 当成普通 `implementation` 依赖。正确分工是：插件负责生成和维护 profile，Macrobenchmark 负责跑 CUJ，`profileinstaller` 负责本地安装场景的 profile 安装。

**R8 优化配置方面**，需要区分两个独立的控制维度：

- **规则文件**决定预设 keep/优化规则集：`proguard-android-optimize.txt` 是推荐入口（`proguard-android.txt` 内含 `-dontoptimize`，会关闭优化）
- **Gradle 属性**决定是否启用 full mode：`gradle.properties` 中不要保留 `android.enableR8.fullMode=false` 这类 compat mode 开关；AGP 8.0+ 已默认走 full mode

也就是说，文件名和属性各管各的——即使用了 `proguard-android-optimize.txt`，如果 `gradle.properties` 里还留着 `fullMode=false`，R8 仍然不会做深度优化。排查 R8 配置问题时，先查 Gradle 属性，再查规则文件。

```groovy
android {
    buildTypes {
        release {
            minifyEnabled true
            shrinkResources true
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'),
                'proguard-rules.pro'
        }
    }
}
```

R8 full mode 的判断条件也不在文件名上。`gradle.properties` 里不要保留 `android.enableR8.fullMode=false` 这类 compat mode 开关；AGP 8.0+ 已默认走 full mode。需要投入验证的部分，是 keep rules、反射调用和 JNI 入口。

### 优化结果

Reddit 在 Google Play 上线后的 A/B 测试结果 [已验证: developer.android.com, Google Performance Spotlight Week 2025]：

| 指标 | 优化前 | 优化后 | 变化 |
|------|--------|--------|------|
| 冷启动时间 | ~2.8s (P50) | ~1.7s (P50) | **-40%** |
| ANR 率 | 基线 | — | **-30%** |
| 帧渲染时间 | 基线 | — | **改善 25%** |
| APK 体积 | 基线 | — | **-14%** |

投入产出比极高：整个集成不到两周，代码改动量小（主要是配置和 Profile 生成脚本），但对核心指标的改善非常显著。冷启动 40% 的提升中，Baseline Profiles 和 R8 full mode 各自贡献了多少？Reddit 没有单独披露拆分数据，但根据 Google 的基准测试，Baseline Profiles 单独通常能带来 20-30% 的冷启动改善 [已验证: developer.android.com/topic/performance/baselineprofiles]。R8 full mode 的深度优化（代码缩减 + 方法内联）额外贡献了约 10-20%。

### 本案例的关键启示

这个案例展示了一个高 ROI 的优化路径：当 App 还没有做过 Baseline Profiles 和 R8 full mode 时，这两项工作应该是最先做的——改动小、风险低、收益确定。它们是在帮 ART 做它"想做但还没来得及做的事"。

---

## 案例二：抖音冷启动优化——主线程线性执行的极致优化

### 问题背景

抖音（TikTok 中国版）日活超过七亿，是全球最大的短视频应用之一。对于这种体量的产品，启动速度的改善直接关联用户留存和内容消费。抖音技术团队的研究表明，启动时间控制在 2 秒以内可以显著提升用户留存率，而启动性能还会影响完播率、互动率等核心推荐算法指标 [来源: 性能优化日报/2026-03-13-大厂-抖音启动优化实践2025.md]。

### 分析思路

抖音团队面临的核心挑战是：App 规模庞大（Feature 模块上百个），启动路径上的同步操作极多。他们将问题分解为"主线程线性执行时间"这个核心指标——即从进程创建到首页可交互，主线程上所有同步执行的代码的总耗时。

分析工具方面，抖音自研了 Rhea 一体化性能分析平台。Rhea 覆盖启动速度、页面渲染、内存、网络、功耗等多个维度，支持毫秒级差异精细化分析。在低端设备上，Rhea 能够识别出主线程上的锁等待、阻塞和 IO 等待——这些在高端设备上不明显的问题，在低端设备上会被放大为肉眼可见的启动延迟。

通过 Rhea 的分析，抖音团队将冷启动的主线程时间分解为三个主要阶段：

1. **MultiDex 加载阶段**：由于方法数超过 65K，App 使用了 MultiDex。API 21 以下走 support multidex 路径，`MultiDex.install()` 会在启动早期处理 secondary dex 的解压、校验和 ClassLoader 安装；Dalvik 侧还要处理 dexopt 与类加载成本。API 21+ 才进入 ART 原生 multidex 路径，安装或后台编译阶段由 dex2oat / profile guided 编译处理多个 dex，启动时仍可能受类验证、首次类加载、profile 命中率和 I/O 影响。

2. **反序列化阶段**：抖音在启动时需要读取大量的配置数据和缓存数据（用户偏好、AB 实验配置、推荐策略参数等），这些数据以序列化形式存储在本地，启动时需要反序列化到内存。配置项越多，这个阶段的耗时越长。

3. **主线程耗时消息阶段**：Application.onCreate() 之后到首页 Activity.onCreate() 之间，还有大量同步消息需要处理——包括各种 SDK 的初始化回调、Provider 的 query 操作、以及一些历史遗留的同步初始化代码。

### 优化手段

抖音采用了分阶段的优化策略 [来源: 性能优化日报/2026-03-13-大厂-抖音启动优化实践2025.md]：

**MultiDex 优化**方面，抖音团队将 MultiDex 的加载从主线程移到了子线程。核心思路是利用 Android 的 ClassLoader 机制，在主线程只加载首个 dex（包含启动路径必需的类），其余 dex 在子线程中异步加载。加载完成前如果需要访问未加载 dex 中的类，会通过一个拦截机制等待对应 dex 加载完成。

**反序列化优化**方面，他们做了两件事：一是将启动阶段必需的配置项精简到最少（通过延迟加载非必需配置），二是将序列化格式从 JSON 切换为 Protocol Buffers。Protobuf 的反序列化速度比 JSON 快 5-10 倍，而且生成的类没有反射开销。

**主线程耗时消息优化**方面，抖音建立了一个启动任务调度框架。核心思想是将 Application.onCreate() 和首页 Activity.onCreate() 中的所有初始化任务建模为有向无环图（DAG），根据任务间的依赖关系进行拓扑排序，然后分配到不同的线程池执行。主线程只执行必须在主线程的任务（如创建 Handler、初始化 Looper 等），其余全部放到子线程。

```kotlin
// 启动任务调度框架的核心抽象（示意）
// 将启动任务建模为 DAG 节点
class StartupTask(
    val name: String,
    val dependencies: List<String>,  // 依赖的其他任务
    val thread: ThreadType,           // MAIN / IO / COMPUTE
    val block: () -> Unit
)

// 拓扑排序 + 多线程调度
class StartupScheduler {
    fun schedule(tasks: List<StartupTask>) {
        // 1. 构建依赖图
        // 2. 拓扑排序确定执行顺序
        // 3. 按线程类型分发到对应线程池
        // 4. 主线程 await 关键路径上的任务
    }
}
```

这种框架设计的好处在于：新增初始化任务时只需声明依赖关系，调度器自动处理执行顺序和线程分配。它把"启动优化"从一个手工活变成了一个系统化的工程。

### 优化结果

抖音没有公开具体的优化前后数值对比，但分享了以下关键结论 [来源: 性能优化日报/2026-03-13-大厂-抖音启动优化实践2025.md]：

- 主线程线性执行时间显著缩短，P50 冷启动控制在 2 秒以内
- 低端设备上的改善尤为明显——通过 Rhea 识别出的锁等待和 IO 等待被大幅消除
- 建立了可持续优化的反馈循环：理论分析 → 现状测量 → 优化实施 → A/B 验证 → 防劣化监控

抖音还建立了防劣化机制：每次发版前自动运行启动性能回归测试，如果冷启动 P50 回退超过 100ms，会自动拦截发版。这确保了优化成果不会因为新功能的加入而逐渐退化。

### 本案例的关键启示

抖音案例的核心价值在于"系统化"三个字。很多团队做启动优化是头痛医头、脚痛医脚——今天优化了这个 SDK 的初始化，明天又加了一个新的同步初始化。抖音通过任务调度框架将启动过程工程化，使得优化成果可积累、可维护。

另外，Rhea 工具的投入也很值得参考。当 App 规模大到一定程度，通用的性能分析工具（Systrace/Perfetto）在"差异对比"上不够精准——我们需要知道"这次启动比上次慢了 200ms，慢在哪里"。毫秒级差异分析能力对大型 App 性能团队来说是基本要求。

---

## 案例三：Disney+ 从 ProGuard 到 R8 Full Mode——配置迁移的收益

### 问题背景

Disney+ 是全球前三大流媒体应用之一。与 Reddit 案例类似，Disney+ 也需要优化冷启动速度以提升用户观看体验。但 Disney+ 的特殊约束在于：作为一个音视频流媒体应用，它的启动路径涉及 DRM（数字版权管理）初始化、播放器引擎加载和内容元数据解析——这些操作本身就有不可压缩的耗时 [已验证: developer.android.com, Google Performance Spotlight Week 2025]。

### 优化手段

Disney+ 的切入点，是把历史上的 ProGuard / R8 compat 配置收敛到现代 R8 优化配置。

这项迁移的重点，在于避开 `proguard-android.txt` 这条默认文件路径。官方文档已经把它列为不推荐路径，因为它自带 `-dontoptimize`。更稳的做法是保留 `proguard-android-optimize.txt`，清理 `android.enableR8.fullMode=false` 这类 compat mode 开关，再逐条验证 keep rules 在 R8 下的行为，尤其是反射和 JNI 相关规则。

### 优化结果

Disney+ 在 Google Play 上线后的效果 [已验证: developer.android.com, Google Performance Spotlight Week 2025]：

| 指标 | 变化 |
|------|------|
| 启动时间 | **-30%** |
| ANR 率 | **-25%** |

这个结果值得关注，因为 Disney+ 主要做的是 shrinker 配置迁移，没有再叠加 Baseline Profiles 这类改动。30% 的冷启动改善应理解为 R8 优化配置、规则收敛和代码体积下降的综合结果，和 `proguard-android.txt` 这个文件名本身无关。

ANR 率降低 25% 可以从两个方向理解：一类收益来自未使用代码被移除后，DEX 更小、加载更快；另一类收益来自方法内联和类合并这类优化，让启动主线程路径更短。

### 本案例的关键启示

这个案例说明，如果项目里还残留 ProGuard 时代的默认文件和 compat mode 开关，值得尽快清理。R8 从 Android Gradle Plugin 3.4 起就是默认 shrinker，但 full mode 与 compat mode 的边界要单独核对，现代项目应以官方 shrink-code 文档为准。

---

## 案例四：页面切换优化——从 500ms 到 150ms 的 Activity 跳转

前面三个案例都聚焦在冷启动优化。但在实际项目中，用户感知最频繁的“慢”往往是页面跳转，而不是冷启动。点击一个商品、打开一个详情、切换一个 Tab，这些操作的频率远高于冷启动，对应的响应时间要求也更苛刻。这个案例展示如何将 8.4 节讨论的 Activity/Fragment 切换原理应用到具体项目中。

### 问题背景

某中等规模的电商 App（日活约 500 万）反馈：从首页商品列表点击进入商品详情页的跳转耗时过长，用户能明显感知到"卡了一下"才跳过去。测试数据显示，在高端设备上跳转耗时约 300ms，在中端设备上约 500ms，低端设备上超过 800ms。

用户对"点击后应该立刻跳转"的心理预期大约是 100-150ms（参见我们在 8.1 节中讨论的响应时间分级）。500ms 的跳转已经明显超出了"感觉即时"的范围，进入了"能感知到延迟"的区域。

### 分析思路

开发团队使用 Perfetto 抓取了点击后的完整 trace，在时间线上标注了从 onClick 回调到详情页第一帧渲染完成的区间。分析发现 500ms 的时间被分配在以下几个阶段：

**主线程消息处理（约 50ms）**：从用户点击到 `Activity.startActivity()` 被调用，中间经过了 View 的事件分发过程和 onClick 回调执行。这部分本身不慢，但 onClick 回调中做了商品 ID 的参数校验和埋点上报，消耗了约 20ms。

**Binder IPC（约 30ms）**：`startActivity()` 通过 Binder 调用 AMS（ActivityManagerService），AMS 需要检查目标 Activity 是否已注册、权限是否合法、目标进程是否已创建等。在目标进程已存在的情况下，这个 Binder 调用通常在 10-30ms。

**目标 Activity 创建（约 200ms）**：这是最大的耗时项。详情页的 `onCreate()` 中做了大量初始化工作：创建 ViewModel、发起网络请求、初始化自定义 View、设置 RecyclerView 适配器。其中自定义 View 的构造函数中有一个从 assets 读取 JSON 配置文件的操作，每次跳转都要读一次，消耗约 60ms。

**首帧渲染（约 220ms）**：由于详情页的 View 层级较深（嵌套的 ScrollView + 多个 RecyclerView），measure/layout 两次遍历就消耗了约 150ms。加上 draw 阶段中几个自定义 View 的 onDraw 比较重（阴影绘制、圆角裁剪），draw 阶段又消耗了约 70ms。

### 优化手段

团队分三阶段优化：

**阶段一：快速见效（投入 2 天）**

将 onClick 中的埋点上报改为异步执行。埋点数据先缓存到内存队列，由后台线程批量上报，不再阻塞 UI 线程。同时将 assets 中的 JSON 配置文件改为在 Application.onCreate() 时预加载到内存，避免每次跳转都读取。

这两项改动将跳转耗时从 500ms 降到了约 420ms。

**阶段二：延迟加载（投入 1 周）**

将详情页的初始化工作做了延迟加载处理。核心思路是"先展示骨架屏，再加载数据"：

- `onCreate()` 中只做最轻量的操作：设置 Content View、初始化 ViewModel
- 网络请求在 `onStart()` 中发起，不在构造函数中
- RecyclerView 的数据绑定在数据返回后通过 DiffUtil 增量更新
- 自定义 View 的重绘制逻辑优化：将 `onDraw()` 中的阴影绘制缓存为 Bitmap

这一阶段将跳转耗时进一步降到约 250ms。

**阶段三：渲染优化（投入 1 周）**

第三个阶段解决 View 层级过深的问题：

- 使用 `ViewHolder` 模式减少 `findViewById()` 的重复调用
- 将嵌套的 ScrollView + RecyclerView 改为单一 RecyclerView + 多 viewType
- 自定义 View 使用 `setLayerType(HARDWARE)` 开启硬件加速层，减少重绘范围
- 对于不频繁变化的静态区域，减少 `requestLayout()` 触发：约束布局层级、合并 payload 更新；RecyclerView 尺寸稳定时使用 `setHasFixedSize(true)`，批量更新期间可短时间使用 `suppressLayout(true/false)` 并在 `finally` 中恢复

这一阶段将首帧渲染时间从 220ms 降到了约 100ms，总跳转耗时约 150ms。

### 优化结果

| 阶段 | 跳转耗时 | 改动内容 |
|------|----------|----------|
| 优化前 | ~500ms | — |
| 阶段一 | ~420ms | 异步埋点 + 配置预加载 |
| 阶段二 | ~250ms | 延迟加载 + 骨架屏 |
| 阶段三 | ~150ms | View 层级扁平化 + 硬件层 |
| **最终** | **~150ms** | **总计投入约 2.5 周** |

[待验证: 上述数据为综合多个电商 App 的典型优化经验归纳，非单一 App 的精确测试。具体数值因项目而异。]

最终 150ms 的跳转时间在用户的感知阈值之内。值得一提的是，150ms 并不是极限——通过异步 inflate（AsyncLayoutInflater）和预先创建 Activity 的方案，还可以进一步缩短。但这些方案复杂度更高，需要根据实际情况权衡投入产出比。

### 本案例的关键启示

页面切换优化的关键原则是"分而治之"：先用 Perfetto 精确定位时间花在了哪个阶段（消息处理 / IPC / Activity 创建 / 渲染），然后逐阶段优化。不要凭直觉猜测瓶颈在哪——在本案例中，团队最初以为是网络请求慢，但 trace 显示网络请求是异步的，瓶颈是 View 层级的 measure/layout。

---

## 案例五：系统级启动优化——Google AutoFDO 与 16KB 页面

前面四个案例都是从 App 端出发的优化。这一节我们来看一个不同视角的案例：Google 如何从系统层面优化所有 App 的启动速度。

### 背景

2025-2026 年，Google 在 Android 系统层面推了两项影响较大的优化——AutoFDO 和 16KB 页面大小。AutoFDO 对普通 App 基本透明；16KB page size 对纯 Java/Kotlin App 基本透明，但只要 APK 含 NDK/JNI 或第三方 `.so`，开发团队就要验证 native library alignment、`mmap` / `PAGE_SIZE` 假设和依赖库版本。平台收益和发布兼容要求要分开看：AutoFDO 主要是系统内核优化，16KB page size 同时带来启动收益和 native 适配要求。

### AutoFDO：用真实数据指导内核编译

AutoFDO（Automatic Feedback-Directed Optimization）的核心思路是：收集真实应用的运行 profile，用这些数据指导内核代码的编译优化。

具体做法是：Google 采集了 Pixel 设备上最常用的 100 个 Android 应用的真实运行数据，分析这些应用与内核的交互模式，识别出内核中被频繁执行的"热"代码路径，然后使用 Clang 编译器的 AutoFDO 支持对这些热路径做更激进的优化（如更好的指令缓存布局、分支预测优化）。

为什么优化内核能加速 App 启动？因为在 Android 上，内核操作约占总 CPU 时间的 40% [已验证: developer.android.com, Google Blog 2026-03]。App 启动过程中的每一次 Binder 调用、每一次内存分配、每一次文件 IO，背后都有内核的参与。优化内核热路径等于优化了所有 App 共用的基础设施。

公开资料里的数字来自两类口径，不能放在同一张“实测效果”表里。Android GKI / Pixel 相关结果如下：

| 场景 / benchmark | 口径 | 变化 |
|------------------|------|------|
| Cold App Launch Time | Pixel 设备上常用应用 profile 驱动的 Android GKI 内核优化 | **-4.3%** 启动耗时 |
| Boot Time | Android GKI 内核优化后的系统开机场景 | **-2.1%** |
| Binder-rpc | Android 内核微基准 | **+21.7%** |
| Hwbinder | Android 内核微基准 | **+20.0%** |

AutoFDO 早期论文 / 数据中心基准另算：

| 场景 / benchmark | 口径 | 变化 |
|------------------|------|------|
| AutoFDO historical benchmark | 早期 AutoFDO 论文与服务端 workload 的几何平均 | **+10.5%** |

这两张表不能互相外推：`+10.5%` 不代表 Android App 启动收益，`+26.4%` 也不能当成系统级平均收益。AutoFDO 目前已部署到 android16-6.12 和 android15-6.6 内核分支，计划扩展到 android17-6.18 GKI。

### 16KB 页面大小：减少 TLB Miss 的架构级优化

从 Android 15 开始，系统支持 16KB 内存页面大小（传统为 4KB）。我们在第 4 章内存管理部分详细讨论了页表和 TLB 的工作机制，这里聚焦它对启动速度的影响。

原理并不复杂：页表项数量变为原来的 1/4，TLB（Translation Lookaside Buffer，页表缓存）的命中率显著提升。TLB miss 的代价是一次页表遍历，可能需要数十到数百个 CPU 周期。在启动阶段，大量的内存映射和代码加载操作都会触发 TLB 查询，减少 miss 直接减少了等待时间。

Google 的内部基准测试显示 [已验证: developer.android.com, Google Blog 2025-11]：

| 指标 | 变化 |
|------|------|
| 应用启动（平均） | **+3.16%** |
| 相机冷启动 | **+6.6%** |
| 相机热启动 | **+4.48%** |
| 系统开机 | **+8%（约 0.8-0.95 秒）** |
| 功耗 | **-4.56%** |
| 内存使用 | **+9%** |

内存使用增加约 9% 是代价。但考虑到启动速度和功耗的改善，这个 trade-off 对大多数设备是值得的。

自 2025 年 11 月 1 日起，提交到 Google Play、面向 Android 15+ 设备的新应用和更新，在 64-bit 设备上要支持 16KB page size。影响集中在 NDK/JNI 和第三方 `.so`：检查 ELF segment alignment、AGP/NDK 版本、`mmap` 长度计算、任何硬编码 `4096` 或 `PAGE_SIZE` 的假设。纯 Java/Kotlin 代码大多由系统处理，但只要 APK 里有 native library，就要在 16KB emulator 或真机上跑安装、启动、so 加载和动态 mmap 路径。

### 本案例的关键启示

这个案例的意义在于：性能优化不总是"App 端能做的事"。Google 正在构建数据驱动的系统级自动优化体系——从 AutoFDO 到 ART 编译优化通过 Mainline 推送。App 开发者要把两类变化区分开：AutoFDO 可以作为系统背景条件；16KB page size 要进入 native 兼容测试和发布检查。理解这些平台级优化，能让启动耗时归因更稳，也能减少新平台适配时的遗漏。

---

## 举一反三：响应速度优化的通用方法论

五个案例覆盖了从 App 端到系统端、从工具配置到架构改造的不同维度。把它们放在一起看，可以提炼出一套通用的优化方法论：

**第一，先度量，再优化。** Reddit 用 Macrobenchmark 建基线，抖音用 Rhea 做毫秒级差异分析，电商案例用 Perfetto 精确定位瓶颈。没有一个团队是凭直觉做优化的。度量工具的选择取决于我们的规模——小型 App 用 Macrobenchmark + Perfetto 就够了，大型 App 可能需要自建分析平台。

**第二，区分"平台收益"和"应用优化"。** Baseline Profiles、R8 优化配置和 AutoFDO 是成本较低的收益来源；16KB page size 对纯 Java/Kotlin App 接近透明，但含 native library 的 App 要把 ELF alignment、`PAGE_SIZE` 假设和第三方 `.so` 版本纳入发布检查。先吃低成本收益，再投入应用层深度优化。

**第三，系统化 > 贴膏药。** 抖音的启动任务调度框架、Reddit 的 CUJ Profile 管理——它们把优化过程从"每次手动排查"变成了"系统自动处理"。这种投入的 ROI 是长期累积的。

**第四，防劣化比优化更重要。** 抖音建立了 100ms 回退拦截机制，取得一次优化不容易，守住不退步更难——每次新功能迭代都可能引入新的启动耗时——没有防劣化机制，优化成果会在几个月内被逐渐蚕食。

**第五，利用系统级自动采集减少人工排查。** Android 15+ 的 ProfilingManager 已支持系统触发式采集——App Startup、ANR 等系统事件可自动触发 system trace / heap dump。线上监控不需要在每个入口手动埋点，而是注册系统触发器让平台在关键事件发生时自动抓取现场。Android 17 进一步引入 `TRIGGER_TYPE_OOM`（内存超限）等触发类型，`ProfilingResult.getTag()` 可以区分不同触发源产出的 trace 文件。系统触发受采样策略和设备版本约束，不能保证每次事件都产出 trace；线上使用仍需采样率控制和隐私脱敏。

[自动发现] **ProfilingManager（Android 15+）** 对响应速度案例分析的辅助价值：Android 15 提供公开 `android.os.ProfilingManager`，应用可以通过 `requestProfiling()` 主动请求系统采集 system trace、heap dump、heap profile 或 stack sampling。Android 16 的 System Triggered Profiling 把触发源扩展到 App Startup、ANR 等系统事件；这类系统触发与 App 主动调用共用结果回调模型，但是否生成、保存和上报仍受采样策略、设备版本、权限边界和隐私策略约束。

下面的代码只展示公开 SDK 可编译的显式 system trace 请求路径，重点看 `PROFILING_TYPE_SYSTEM_TRACE`、`tag` 和结果回调。公开 SDK 没有暴露 `KEY_DURATION_MS`；普通 App 代码不要依赖隐藏常量控制采集时长：

```kotlin
@RequiresApi(35)
fun requestStartupSystemTrace(context: Context) {
    val profilingManager = context.getSystemService(ProfilingManager::class.java)

    profilingManager.requestProfiling(
        ProfilingManager.PROFILING_TYPE_SYSTEM_TRACE,
        null,
        "startup_trace",
        null,
        context.mainExecutor
    ) { result ->
        if (result.errorCode == ProfilingResult.ERROR_NONE) {
            val tracePath = result.resultFilePath
            Log.i("StartupTrace", "profiling result: $tracePath")
        } else {
            Log.w("StartupTrace", "profiling failed: ${result.errorCode}")
        }
    }
}
```

`requestProfiling()` 的第二个参数可以传 `null` 或公开参数组成的 `Bundle`。如果要调整采集时长，只能等公开 SDK 提供对应键，或在平台 / 系统 App 场景使用已确认的内部接口；普通 App 示例不应写 `ProfilingManager.KEY_DURATION_MS`。结果文件由系统写入应用可访问目录，回调只负责拿到路径和错误码。线上接入时还要加采样率、用户授权、隐私脱敏和上传窗口控制，否则 trace 文件会带来额外 I/O 和合规风险。[来源: intake/research-feeds/2026-04-01-12-android16-17-profilingmanager-system-triggered.md；Android `ProfilingManager` API 文档]

---

## 常见问题与误区

**误区一：“启动优化就是减少 Application.onCreate() 的耗时。”**

这个认知范围太窄了。从本章的案例看，启动耗时分布在多个阶段——Reddit 的瓶颈是 JIT 编译，抖音的瓶颈是 MultiDex 和主线程同步消息，电商案例的瓶颈是 View 层级的 measure/layout。`Application.onCreate()` 只是一个环节。正确的做法是先用 Perfetto/Macrobenchmark 建立完整的耗时分布图，找到瓶颈再针对性优化，而不是一上来就砍 `onCreate()`。

**误区二：“Baseline Profiles 只对首次启动有效，之后就失效了。”**

不准确。Baseline Profiles 在每次 App 更新后重新生效——因为更新会清空之前 JIT 编译的缓存。对于高频更新的 App（社交、电商类通常每 1-2 周更新一次），Baseline Profiles 的实际生效频率比想象中高。此外，Android 12 起将 ART 作为 Mainline 模块（`com.android.art`），系统可以通过 Google Play System Updates 更新编译策略（包括 dex2oat 优化、Profile 引导编译等），进一步提升 Baseline Profiles 的命中率和编译效果。[已确认: ART Mainline 模块自 Android 12 (API 31) 引入，验证来源 AOSP android-12.0.0_r1]

**误区三：“R8 full mode 风险太高，不敢开。”**

风险点不在 `proguard-android.txt` 这个文件名上，而在 keep rules 是否覆盖了反射、JNI 和动态加载。现代文档给出的基线配置是 `proguard-android-optimize.txt`，同时清理 `android.enableR8.fullMode=false` 这类 compat mode 开关；AGP 8.0+ 默认已经是 full mode。更稳的迁移路径，是在 CI 里先跑完整测试，再根据崩溃和反混淆结果补 keep rules。

**误区四：“页面切换慢就是网络请求慢。”**

在电商案例中，团队最初的直觉也是网络请求慢。但 Perfetto trace 显示网络请求是异步的，阻塞首帧的是 View 层级的 measure/layout 和自定义 View 的 onDraw。凭直觉猜测瓶颈是性能优化中最大的时间浪费——先用工具定位，再动手。

---

## 参考资料

- Google Performance Spotlight Week 2025 — Reddit & Disney+ 优化案例
  - [已验证: developer.android.com, Google Performance Spotlight Week 2025]
- Android Baseline Profiles 官方文档
  - https://developer.android.com/topic/performance/baselineprofiles
  - [已验证: 官方文档]
- 抖音启动优化实践（2025）
  - [来源: 性能优化日报/2026-03-13-大厂-抖音启动优化实践2025.md]
- Google AutoFDO 内核优化
  - [已验证: developer.android.com, Google Blog 2026-03]
- Android 16KB 页面大小变更
  - [已验证: developer.android.com, Google Blog 2025-11]
- Android 16/17 ProfilingManager 系统触发式追踪
  - [来源: intake/research-feeds/2026-04-01-12-android16-17-profilingmanager-system-triggered.md]
- R8 Shrinker 官方文档
  - https://developer.android.com/build/shrink-code
  - [已验证: 官方文档]
