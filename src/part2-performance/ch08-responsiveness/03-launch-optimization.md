---
title: "启动优化策略"
chapter: "8.3"
status: finalized
polish_count: 1
polish_date: "2026-04-06"
polish_by: "task2b-polish"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-06-06"
last_verified_against: "Android Developers launch-time/SplashScreen/Baseline Profiles/App Startup docs + Android 17 behavior changes + AOSP android-16.0.0_r1 ActivityThread/ViewStub"
confidence: medium
sources:
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-12_wechat_SplashScreen_优化启动体验_开发者说_DTalk.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_性能优化_如何优雅实现_App_秒开.md"
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-06_wechat_淘宝页面首帧优化的经验和心得_1.md"
  - type: blog
    path: "Cubox/Activity 启动速度分析方法（启动流程分析） - Light.Moon-2022-04-11.md"
  - type: blog
    path: "Cubox/Android 强推的 Baseline Profiles 国内能用吗？我找 Google 工程师求证了！ - 掘金-2022-07-17.md"
  - type: official
    path: "developer.android.com/topic/performance/vitals/launch-time"
  - type: official
    path: "developer.android.com/guide/topics/ui/splash-screen"
  - type: official
    path: "developer.android.com/topic/performance/baselineprofiles"
  - type: official
    path: "developer.android.com/topic/libraries/app-startup"
  - type: official
    path: "developer.android.com/about/versions/17/behavior-changes-17"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/ViewStub.java"
tags: ['startup-optimization', 'lazy-init', 'splash-screen', 'baseline-profile', 'app-startup', 'content-provider', 'async-inflate', 'task-scheduler']
related_chapters: ["8.1", "8.2", "2.4", "2.5", "7.5", "1.10", "1.12", "8.7"]
section: "8.3"
drafted_by: "openclaw-task2a"
drafted_date: "2026-04-01"
task9_state: "reviewed"
task2b_result: fixed
task9_result: auto-fixed
task9_reviewed_date: "2026-06-06"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-06T16:20:00+08:00"
repaired_date: "2026-04-27"
repaired_by: "openclaw-task2b"
last_task2b_at: "2026-04-27T10:44:00+08:00"
review_notes: "2026-04-30 task9 deep-review: needs-rework。P0 0，P1 2，P2 2。Startup Profile 原问题部分已覆盖；external DEFAULT_TO_WEB 线索未采纳。"
task6_state: "reviewed"
task6_result: "pass-light-edit"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-05-09"
pipeline_stage: "ready-to-publish"
review_round: 4
last_task6_at: "2026-05-09T06:05:00+08:00"
last_task6_review_log: "logs/review/2026-05-09-06-review.md"
task6_review_notes: "2026-05-09 Task6 06:05：Task2B 修复后写作复审；轻修 8 处（结构性元叙述、主观标题、模糊/口号化表达、无条件量化表述），L1/L2 通过；无新增 L3/L4 回炉项，送 Task9 复审。"
last_task9_review_log: "logs/deep-review/2026-06-06-16-audit.md"
task9_review_notes: "2026-06-06 Task9 闲时抽检 auto-fix：Android 17 行为变更已公开 MessageQueue lock-free 实现；补齐版本差异并将 master AOSP 参考锚点降到 android-16.0.0_r1，回到 Task6 复审。"
last_task6_audit: "2026-07-07"
deepseek_polish_state: done
last_deepseek_polish_at: 2026-05-27
last_task9_autofix_at: "2026-06-06"
last_task9_audit: "2026-06-06"
task2b_state: fixed
last_task2b_verifier_at: "2026-06-14T11:25:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-06-14-11-task2b-verifier.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-14
---

# 启动优化策略

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 延迟初始化策略：按需加载、懒加载、异步初始化
- 🔹 Splash Screen（Android 12+ SplashScreen API）的正确使用
- 🔹 多线程并行初始化框架设计：拓扑排序、依赖管理
- 🔹 ContentProvider 优化：减少 auto-init 的库数量
- 🔹 布局优化对首帧速度的影响：减少 inflate 耗时、ViewStub、异步 inflate
- 🔹 Baseline Profile 的制作与效果量化

### 扩展（可选深入）

- 🔸 大型 App 的启动框架设计（如 Task 编排系统）
- 🔸 启动速度的线上监控与回归检测

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 启动优化：时间花在哪、怎么省

上一节（8.2 App 启动全流程）已经梳理了从用户点击图标到首帧绘制的冷启动路径。在 Perfetto 中打开一个中等复杂度应用的冷启动 Trace，常会看到从 `BindApplication` 到 `performTraversals` 之间有 1-3 秒的间隔——这段时间里，Application 在初始化十几个 SDK，Activity 在 inflate 一个复杂的布局，ContentProvider 在默默加载各种库。这些操作串行堆积在主线程上，就构成了用户感知到的"启动慢"。

了解启动流程是为了知道"时间花在哪里"；启动优化要解决的是"怎么把时间省下来"。它会牵涉任务编排、布局优化、编译优化和线上监控等多个层面。每个优化手段都有适用场景和副作用，盲目套用可能适得其反。

具体策略需要绑定两个衡量启动速度的指标：**TTID（Time To Initial Display）**和 **TTFD（Time To Full Display）**。

TTID 是从用户触发启动到应用绘制第一帧的时间。对应 `am start -W` 输出中的 `TotalTime`，也对应 Perfetto 中 `Choreographer#doFrame` 第一次出现的时间点。TTID 衡量的是"用户看到了画面"——但这个画面可能只是骨架屏或 Loading 状态。

TTFD 是从用户触发启动到应用内容完全就绪的时间。终点需要开发者在代码中调用 `Activity.reportFullyDrawn()` 来标记。没有调用 `reportFullyDrawn()` 的话，系统无法知道应用何时内容已经完整可交互。TTFD 衡量的是"用户看到的是完整内容"。

两者可能差距很大。一个新闻 App 的 TTID 可能只有 800ms（首帧显示了骨架屏），但 TTFD 要 2 秒（首页新闻列表从服务端加载完成）。这里有三个容易混在一起的时间点：`Activity.reportFullyDrawn()` 早在 API 19 就已经提供，用来告诉系统“内容已经完整可交互”；`FrameMetrics` 和 `FrameMetrics#TOTAL_DURATION` 则是 API 24 引入的帧耗时观测能力；Android 12（API 31）新增的是 SplashScreen API 和更统一的启动体验规范。另一个容易误判的点是：Android 12+ 如果应用在系统判定 TTID 之前就调用 `reportFullyDrawn()`，系统会把这次 TTFD 记成 TTID，避免过早上报把启动耗时做小。

优化策略必须针对正确的指标：TTID 优化侧重减少主线程阻塞（延迟初始化、布局优化、ContentProvider 精简），TTFD 优化还需要考虑数据预加载、网络策略、以及 `reportFullyDrawn()` 的合理调用时机。

目标是：面对一个启动耗时 2 秒以上的应用，能判断时间主要花在了哪个环节（SDK 初始化？布局 inflate？DEX 编译？），再选择对应的优化策略组合，而不是上来就"把所有 SDK 改成异步初始化"。

## 优化策略全景：一张图看清四个维度

启动优化策略可以从四个维度来理解：

**维度一：减少主线程的工作量。** 这是最直接的优化方向——把不需要在主线程同步完成的任务移走，或者干脆不做。延迟初始化、异步初始化、ContentProvider 优化、布局优化都属于这一类。

**维度二：利用并发加速必要的工作。** 有些任务必须在启动阶段完成，但彼此之间没有依赖关系，可以通过多线程并行执行来缩短总耗时。多线程并行初始化框架、Task 编排系统属于这一类。

**维度三：改善用户感知。** 有些耗时是无法避免的（比如网络请求），但可以通过 Splash Screen、骨架屏等手段让用户觉得"App 已经准备好了"，而不是盯着白屏发呆。

**维度四：提前编译热点代码。** ART 的 JIT/AOT 编译策略会影响启动时执行 DEX 代码的效率。Baseline Profile 和 Cloud Profile 通过提前告诉系统"哪些代码路径在启动时会被执行"，让系统在安装时就编译好这些热点方法，减少启动时的解释执行和 JIT 编译开销。

[图：启动优化四维策略全景图——横轴为"减少工作量 / 加速执行 / 改善感知 / 提前编译"，纵轴为"应用侧可做 / 系统侧可做 / 需要两者配合"]


## 延迟初始化策略：把"现在就要"变成"用的时候再说"

[已验证: 来源见 developer.android.com/topic/performance/vitals/launch-time 及多个行业实践]

### 分类原则：区分"必须同步完成"和"可以延后"

启动阶段主线程上执行的每一行代码都在消耗启动时间。而很多在 Application.onCreate 和 Activity.onCreate 中执行的初始化逻辑，并不需要在首帧绘制前完成。

以一个典型的内容类应用为例，启动阶段可能执行了 20-30 个 SDK 的初始化。仔细分析下来，首帧显示依赖的通常只有 UI 框架、网络库（用于加载首页数据）、图片加载库这几个。其他如推送 SDK、统计 SDK、热修复 SDK、广告 SDK 等，完全可以等到首页显示后再初始化。

这背后的分类逻辑是这样的：

**必须同步初始化的任务**：首帧绘制路径上的依赖——UI 框架、主题系统、首页必需的网络请求和数据加载。这些任务如果延迟，用户看到的首页会是空白的或者出错的。

**可以异步初始化的任务**：不影响首帧显示的后台服务——推送、统计、热修复等。这些任务可以立即提交到后台线程执行，不阻塞主线程。

**可以延迟到使用时再初始化的任务**：二级页面或特定功能才需要的模块——地图 SDK（只在用户打开地图页面时才需要）、支付 SDK（只在用户发起支付时才需要）等。这些任务用懒加载（Lazy Load）策略，第一次使用时才初始化。

**16KB 页面下启动期 COW 场景的写操作克制**：除了上面三种策略分类，Android 15 之后还有一个容易被忽略的启动开销来源：16KB 页面设备上，COW 粒度从 4KB 扩大到 16KB。COW 只在写入共享页或 Zygote 继承页时触发——App 自己分配的堆对象、已私有页的后续写入、文件映射写入都不会额外触发。需要关注的是 Zygote fork 后首次写入继承页的场景：这类页在 fork 时标记为共享，首次写入触发 16KB 粒度的 COW，比 4KB 页多拷贝 4 倍物理内存。启动阶段如果对 Zygote 继承的静态字段、共享配置对象、class 字段做大量写入，COW 开销会叠加。建议的做法：启动初期避免对 Zygote 继承的数据结构做批量写入，延迟到首页显示后再执行。

[待验证: 缺少同设备 4KB/16KB 的 minor faults / PSS / CPU 时间对照 trace 数据，当前描述基于源码级 COW 机制推导]

### 异步初始化的正确姿势

异步初始化不是简单地 `new Thread(() -> initSDK()).start()`。它需要考虑线程安全、初始化顺序依赖、以及失败处理。

```java
// 一个简单的异步初始化示例
// 注意：这只是基本模式，生产环境建议使用成熟的启动框架
Executors.newSingleThreadExecutor().execute(() -> {
    // 这些 SDK 不依赖主线程，可以安全地在后台初始化
    AnalyticsSDK.init(app);
    PushSDK.init(app);
    CrashReportSDK.init(app);
});
```

这里有几个容易踩的坑：

**第一，Context 的使用。** 很多 SDK 的 init 方法接受 Context 参数，在后台线程中使用 Application Context 是安全的，但如果 SDK 内部尝试获取 Activity Context 或者操作 UI，就会出问题。在把一个 SDK 改为异步初始化之前，需要确认它不会在 init 过程中创建 UI 组件。

**第二，初始化顺序。** SDK 之间可能存在依赖关系——比如支付 SDK 依赖用户登录状态，而登录状态又依赖网络库的初始化。如果把它们都简单地丢到后台线程，可能支付 SDK 在网络库还没准备好时就开始初始化了。对于有依赖关系的初始化任务，需要使用拓扑排序来安排执行顺序（后面会详细讲）。

**第三，时序竞争。** 如果异步初始化的 SDK 在后台还没完成时，用户已经触发了需要该 SDK 的操作（比如用户飞快地点击了一个需要统计 SDK 的按钮），就会遇到 SDK 未初始化的问题。解决方案通常有两种：一是在关键路径上加一个 `CountDownLatch` 或 `await()`，让需要该 SDK 的操作等待初始化完成；二是做好 SDK 未初始化时的降级处理（比如统计事件先缓存，SDK 初始化完成后批量上报）。

### 懒加载：用到时再初始化

懒加载（Lazy Initialization）是延迟初始化的一种特例——在第一次实际使用时才初始化（区别于启动时异步初始化）。这是对启动时间贡献最大的优化手段之一，因为它把初始化开销从启动阶段完全移除了。

```kotlin
// Kotlin by lazy 实现懒加载
val locationManager by lazy {
    LocationManager.getInstance(application)
}

// 首次访问 locationManager 时才会触发初始化
// 如果用户在这次启动中从未使用定位功能，初始化就永远不会发生
```

懒加载最适合的场景是"不一定会在每次启动中都用到的功能"。对于一个有十几个功能模块的应用，用户每次打开应用可能只用到其中的 3-4 个，剩下的 7-8 个模块完全可以懒加载。

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06_wechat_性能优化_如何优雅实现_App_秒开.md]

实际案例中，某内容类应用通过梳理启动任务，将 30 个初始化任务分类后：保留 5 个必须同步的，12 个改为异步，13 个改为懒加载。仅此一项就将冷启动耗时从 2800ms 降到了 1800ms。

### 在 Perfetto 中验证延迟初始化的效果

延迟初始化优化前后，在 Perfetto 中对比：

- **优化前**：主线程在 `Application.onCreate` 中有大量的 CPU 活动（一段厚厚的执行块），对应的是 SDK 的同步初始化。主线程在这段期间持续运行，没有 idle。
- **优化后**：`Application.onCreate` 变得很薄（可能只有几十毫秒），因为大部分 SDK 已经被移到后台线程或延迟了。其他线程上可能会出现初始化活动，但不阻塞首帧绘制。

在 Perfetto 中具体看的方法：搜索 `BindApplication` slice，观察其结束后到 `Choreographer#doFrame` 第一次出现之间的主线程活动。这段区域越薄越好。

## Splash Screen：让用户感觉"快了"而不是"在等"

[已验证: 来源见 developer.android.com/guide/topics/ui/splash-screen 及 obsidian/Personal-Knowlodge/source/2026-03-12_wechat_SplashScreen_优化启动体验_开发者说_DTalk.md]

### 为什么需要 Splash Screen

冷启动时，从用户点击图标到应用完成首帧绘制，有一段时间窗口系统会显示一个"启动画面"（Starting Window）。在 Android 12 之前，这个画面是一个纯白色的窗口，背景是应用的 theme 中 `windowBackground` 指定的颜色或图片。很多开发者会通过自定义 `windowBackground` 来显示一个品牌 Logo，让用户觉得应用"已经在启动了"。

但这套方案有几个问题：不同厂商对 Starting Window 的实现有差异，部分厂商会裁剪或替换自定义的 windowBackground；开发者需要自己处理从 Starting Window 到应用内容的过渡动画；在 Android 12+ 上，系统默认的 Starting Window 行为发生了变化，不适配的话可能出现闪烁。

Android 12 引入了全新的 SplashScreen API，统一了启动画面的行为和样式，并提供了兼容库（`androidx.core:core-splashscreen`）支持回退到 Android 5.0（API 21）。

### SplashScreen API 的核心使用

SplashScreen API 的设计理念是：启动画面由系统管理生命周期，开发者只需要配置样式，不需要手动管理"什么时候显示、什么时候消失"。

在 `res/values/themes.xml` 中配置启动画面主题：

```xml
<style name="Theme.App.Starting" parent="Theme.SplashScreen">
    <!-- 启动画面背景色 -->
    <item name="windowSplashScreenBackground">@color/brand_background</item>
    <!-- 中间显示的图标（可以是 AnimatedVectorDrawable） -->
    <item name="windowSplashScreenAnimatedIcon">@drawable/splash_icon</item>
    <!-- 动画时长，最大 1000ms -->
    <item name="windowSplashScreenAnimationDuration">1000</item>
    <!-- 启动画面结束后的 Activity 主题 -->
    <item name="postSplashScreenTheme">@style/Theme.App</item>
</style>
```

然后在 AndroidManifest.xml 中将这个主题设置给启动 Activity（或 Application）：

```xml
<activity
    android:name=".MainActivity"
    android:theme="@style/Theme.App.Starting" />
```

在 Activity 中需要调用 `installSplashScreen()` 来激活兼容库：

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        val splashScreen = installSplashScreen()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        // ...
    }
}
```

`installSplashScreen()` 必须在 `setContentView()` 之前调用，否则 `postSplashScreenTheme` 无法正确切换，可能导致 Activity 使用了错误的主题而崩溃。

### 让启动画面"等一下再消失"

默认行为是：应用绘制第一帧后，启动画面立即消失。但在实际场景中，启动画面有时需要多停留一会儿——比如等待首页数据从网络加载完成再显示内容，或者等待开屏广告加载完成。

SplashScreen 提供了 `KeepOnScreenCondition` 来实现这个需求：

```kotlin
val splashScreen = installSplashScreen()

// 设置一个条件：当条件为 true 时，启动画面保持显示
var dataReady = false
splashScreen.setKeepOnScreenCondition { !dataReady }

// 在后台加载数据，完成后设为 true
viewModel.loadHomeData.observe(this) { data ->
    dataReady = true
    // 启动画面会在下一次检查时消失
}
```

这种方式比旧的 `ViewTreeObserver.OnPreDrawListener` 更简洁，不需要手动管理 listener 的注册和移除。

### 退出动画：从启动画面到应用内容的平滑过渡

SplashScreen API 还支持自定义退出动画，让启动画面平滑过渡到应用内容：

```kotlin
splashScreen.setOnExitAnimationListener { splashScreenViewProvider ->
    val splashScreenView = splashScreenViewProvider.view

    // 计算动画剩余时长（如果启动画面有动画的话）
    val animationDuration = splashScreenViewProvider.iconAnimationDurationMillis
    val animationStart = splashScreenViewProvider.iconAnimationStartMillis
    val remainingDuration = (animationDuration + animationStart) - System.currentTimeMillis()

    val slideUp = ObjectAnimator.ofFloat(
        splashScreenView, View.TRANSLATION_Y,
        0f, -splashScreenView.height.toFloat()
    )
    slideUp.interpolator = AnticipateInterpolator()
    slideUp.duration = min(remainingDuration, 300L)
    slideUp.doOnEnd { splashScreenViewProvider.remove() }
    slideUp.start()
}
```

退出动画的实现需要注意一点：在 Android 12+ 上，启动画面的中间图标有圆形遮罩（遵循 Adaptive Icon 的规范），设计图标时需要确保在圆形区域内完整显示。低版本（通过兼容库）没有这个遮罩限制，但动画也只会显示第一帧。

### 从旧方案迁移到 SplashScreen API

如果应用之前通过自定义 `windowBackground` 实现启动画面，迁移到 SplashScreen API 时需要注意：

1. 移除旧的 `windowBackground` 自定义主题
2. 添加 SplashScreen 兼容库依赖（`androidx.core:core-splashscreen:1.0.1` 或更高版本）
3. 创建 `Theme.SplashScreen` 的子主题，配置启动画面样式
4. 在 Activity 中调用 `installSplashScreen()`
5. 测试低版本兼容性——兼容库在低版本上不支持图标动画和品牌图片


## 多线程并行初始化框架：把串行变并行

[已验证: 来源见多个行业实践及 developer.android.com/topic/libraries/app-startup]

### 为什么需要并行初始化框架

当应用的 SDK 数量增长到 10 个以上时，简单的异步初始化方案就开始力不从心了。原因有三个：

**依赖管理困难。** SDK A 依赖 SDK B，SDK B 依赖 SDK C——这种链式依赖在简单异步方案中很难保证顺序，经常出现 B 还没初始化完 A 就开始调用的情况。

**线程管理混乱。** 如果每个 SDK 都开一个线程初始化，应用启动时可能有十几个线程同时竞争 CPU 和 I/O 资源，反而比串行更慢。特别是在低端设备上，过多的并发线程会导致严重的 CPU 争用和上下文切换开销。

**缺乏全局视图。** 无法看到所有初始化任务的执行状态、耗时和依赖关系，排查启动问题时缺少清晰的定位依据。

并行初始化框架的基本模型是：**把所有初始化任务建模成一个有向无环图（DAG），用拓扑排序确定执行顺序，在依赖约束下最大化并行度。**

### DAG 模型与拓扑排序

每个初始化任务定义为一个 Node，Node 之间通过依赖关系连接：

```
  NetworkSDK ──→ LoginSDK ──→ UserProfileSDK
                    │
                    └──→ PushSDK
  AnalyticsSDK ──→ CrashReportSDK
  
  UIInitSDK（无依赖，可立即执行）
```

在这个 DAG 中：
- `NetworkSDK` 和 `AnalyticsSDK` 和 `UIInitSDK` 没有前置依赖，可以立即并行执行
- `LoginSDK` 依赖 `NetworkSDK`，必须等网络库初始化完成
- `PushSDK` 依赖 `LoginSDK`，需要等登录完成获取到用户标识
- `UserProfileSDK` 依赖 `LoginSDK`
- `CrashReportSDK` 依赖 `AnalyticsSDK`

拓扑排序后的执行计划是：
- 第一层（并发）：NetworkSDK、AnalyticsSDK、UIInitSDK
- 第二层（并发）：LoginSDK、CrashReportSDK
- 第三层（并发）：PushSDK、UserProfileSDK

这样 8 个串行初始化的任务变成了 3 层并发执行。这组数字只用于估算上限，不当成通用收益数据：

**串行执行**：8 个任务每个平均耗时 100ms，总耗时约 800ms
**3 层并行执行**：第一层(3个)约 100ms，第二层(2个)约 100ms，第三层(2个)约 100ms，总耗时约 300ms

真实收益取决于 CPU 核数、锁竞争、I/O 阻塞、SDK 内部同步依赖和主线程回切次数。实施时用 Perfetto、Macrobenchmark 或 `adb shell am start -W` 对比同一版本的串行/并行实现，不要直接套用示例里的百分比。

### Jetpack App Startup Library

Google 在 2020 年推出了 Jetpack App Startup 库（`androidx.startup:startup-runtime`），提供了一个轻量级的初始化框架。

App Startup 的主要接口是 `Initializer<T>`：

```java
public interface Initializer<T> {
    T create(@NonNull Context context);
    List<Class<? extends Initializer<?>>> dependencies();
}
```

每个 SDK 的初始化逻辑封装在一个 `Initializer` 实现类中：

```java
public class NetworkInitializer implements Initializer<NetworkSDK> {
    @Override
    public NetworkSDK create(Context context) {
        NetworkSDK.init(context);
        return NetworkSDK.getInstance();
    }

    @Override
    public List<Class<? extends Initializer<?>>> dependencies() {
        return Collections.emptyList(); // 无前置依赖
    }
}

public class LoginInitializer implements Initializer<LoginSDK> {
    @Override
    public LoginSDK create(Context context) {
        LoginSDK.init(context);
        return LoginSDK.getInstance();
    }

    @Override
    public List<Class<? extends Initializer<?>>> dependencies() {
        return Arrays.asList(NetworkInitializer.class); // 依赖网络库
    }
}
```

App Startup 会自动分析所有 `Initializer` 的依赖关系，构建 DAG 并拓扑排序，然后按依赖顺序同步执行。`InitializationProvider` 在启动阶段触发 `AppInitializer.discoverAndInitialize()`，`doInitialize()` 也会逐个调用 `initializer.create(context)`；没有依赖关系的节点只是少了前置约束，不会被库自动并行化。要并发，只能在 `create()` 内自己切后台，或者使用自研调度框架。

在 `AndroidManifest.xml` 中注册：

```xml
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    android:exported="false"
    tools:node="merge">
    <meta-data
        android:name="com.example.app.NetworkInitializer"
        android:value="androidx.startup" />
    <meta-data
        android:name="com.example.app.LoginInitializer"
        android:value="androidx.startup" />
</provider>
```

App Startup 的优点是简单、官方维护、与 ContentProvider 机制集成（后面会讲）。缺点是功能比较基础——不支持异步执行（所有 `Initializer` 都在主线程执行），不支持条件初始化（比如只在用户登录后初始化某些 SDK），不支持延迟初始化。

[已验证: AndroidX startup-runtime AppInitializer.java / InitializationProvider.java]

### 自研并行初始化框架的关键设计

大型应用通常需要比 App Startup 更强大的框架。自研框架需要处理这些设计点：

**线程池分级。** 不是所有初始化任务都适合在高并发线程池中执行。I/O 密集型任务（读数据库、读配置文件）和 CPU 密集型任务（JSON 解析、加密计算）应该使用不同的线程池。通常的做法是分为 CPU 线程池（核心数等于 CPU 核心数）和 I/O 线程池（核心数较大，如 2 * CPU 核心数）。

**主线程任务与异步任务混合编排。** 有些任务必须在主线程执行（比如 UI 相关的初始化），有些可以在后台执行。框架需要支持"主线程任务作为 DAG 中的一个节点"——当后台任务依赖一个主线程任务时，后台任务需要等待主线程任务完成后才能开始。

**任务超时与降级。** 某个初始化任务如果卡住了（比如网络请求超时），不应该阻塞整个启动流程。框架应该支持为每个任务设置超时时间，超时后跳过该任务并触发降级逻辑。

**监控与日志。** 框架应该自动记录每个初始化任务的开始时间、结束时间、执行线程、是否成功等信息，方便后续分析和优化。

[待补充：并行初始化框架的执行时序图]

## ContentProvider 优化：消除隐式的启动开销

[已验证: 来源见 developer.android.com/topic/libraries/app-startup 及 AOSP androidx.startup 源码]

### 隐式初始化的陷阱

很多第三方库为了简化接入流程，选择了通过 ContentProvider 来实现自动初始化。开发者只需要在 build.gradle 中添加一行依赖，库就会在应用启动时自动完成初始化，无需手动调用 init 方法。

实现方式是：库在自己的 AndroidManifest.xml 中注册一个 ContentProvider，在该 ContentProvider 的 `onCreate()` 中执行初始化逻辑。启动时系统会在 `ActivityThread#handleBindApplication` 中创建 `Application` 对象，接着执行 `installContentProviders()`，随后才进入 `Application.onCreate()`；所以 Provider 初始化仍然会卡在主线程上，而且发生在应用自己的 `Application.onCreate()` 之前。

这个方案对开发者来说很方便，但会把启动成本隐藏到系统创建 Provider 的阶段。一个集成了 10 个以上第三方库的应用，可能有 5-6 个甚至更多的 ContentProvider 在启动阶段串行执行。每个 ContentProvider 的 `onCreate()` 通常耗时 10-50ms，集成了 5-6 个这类库的话，累积 50-300ms 的额外启动时间并不少见。

更麻烦的是，这些隐式初始化通常没有出现在业务代码中，很容易被忽略。Perfetto 中能看到 `BindApplication` 阶段有一段比较厚的主线程活动，其中就包含了 ContentProvider 的初始化，但在代码中可能找不到对应的调用。

### 发现隐式的 ContentProvider 初始化

要找出哪些库通过 ContentProvider 自动初始化，最直接的方法是查看合并后的 AndroidManifest.xml：

```bash
# 在 build 目录下查找合并后的 manifest
cat app/build/intermediates/merged_manifests/debug/AndroidManifest.xml | \
    grep -A 5 "androidx.startup\|InitProvider\|auto-init"
```

或者使用 Android Studio 的 "Analyze APK" 功能，查看 APK 中的 AndroidManifest.xml，搜索所有的 `<provider>` 声明。

常见的通过 ContentProvider 自动初始化的库包括：LeakCanary、WorkManager、Firebase Analytics、Google Play Services、Facebook SDK 等。

### 使用 App Startup 合并 ContentProvider

Jetpack App Startup 库的设计初衷之一就是解决这个问题。它提供了一个统一的 `InitializationProvider`（一个 ContentProvider），所有使用 App Startup 的库的初始化逻辑都通过这个唯一的 ContentProvider 来触发。

原理是：每个库不再注册自己的 ContentProvider，而是通过 `<meta-data>` 声明自己的 `Initializer` 类，注册到 `InitializationProvider` 中。系统只需要初始化一个 ContentProvider，然后在这个 ContentProvider 内部按依赖顺序执行所有 `Initializer`。

```xml
<!-- 合并前：3 个 ContentProvider -->
<provider android:name="com.lib1.InitProvider" ... />
<provider android:name="com.lib2.InitProvider" ... />
<provider android:name="com.lib3.InitProvider" ... />

<!-- 合并后：1 个 ContentProvider -->
<provider
    android:name="androidx.startup.InitializationProvider"
    android:authorities="${applicationId}.androidx-startup"
    android:exported="false"
    tools:node="merge">
    <meta-data android:name="com.example.Lib1Initializer" android:value="androidx.startup" />
    <meta-data android:name="com.example.Lib2Initializer" android:value="androidx.startup" />
    <meta-data android:name="com.example.Lib3Initializer" android:value="androidx.startup" />
</provider>
```

从 3 个 ContentProvider 减少到 1 个，不仅减少了 ContentProvider 创建和初始化的系统开销，还让初始化逻辑集中管理，方便排查和优化。

### 移除不需要的自动初始化

对于不需要在启动阶段初始化的库，可以完全禁用其 ContentProvider 自动初始化（关于 ContentProvider 在启动流程中的完整机制分析，可以参考 1.10 节）：

```xml
<!-- 禁用库的自动初始化 -->
<provider
    android:name="com.lib.InitProvider"
    android:authorities="${applicationId}.com-lib-initprovider"
    tools:node="remove" />
```

然后在代码中手动控制初始化时机：

```kotlin
// 在合适的时机手动初始化
ApplicationScope.launch(Dispatchers.IO) {
    SomeLib.init(applicationContext)
}
```

这种方式最灵活，但也意味着需要自行管理初始化时机和线程安全。

## 布局优化对首帧速度的影响

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06_wechat_淘宝页面首帧优化的经验和心得_1.md 及多个行业实践]

### 布局 inflate 为什么慢

在冷启动流程中，从 Activity.onCreate 调用 `setContentView()` 到 View 树构建完成（inflate、measure、layout），这一段在 Perfetto 中对应主线程上的 `inflate` 和 `performTraversals` slice。对于一个复杂的首页布局，这个过程可能消耗 100-500ms。

布局 inflate 慢的原因有三个：

**XML 解析的开销。** setContentView 需要将 XML 文件解析成 Java/Kotlin 对象。XML 解析本身是 CPU 密集型操作，而且涉及到大量的字符串处理和反射调用。布局越复杂（嵌套层级越深、View 数量越多），解析越慢。

**View 对象创建的开销。** 每个 View 的创建都涉及到构造函数调用、AttributeSet 解析、默认属性设置。对于自定义 View，构造函数中可能还有额外的初始化逻辑。

**measure 和 layout 的递归开销。** inflate 完成后，View 树需要进行 measure 和 layout 两次遍历。嵌套层级越深，递归次数越多。特别是使用了多层嵌套的 LinearLayout（weight 属性会导致二次 measure），性能影响更大。

### ViewStub：延迟加载不可见的布局

ViewStub 是一种轻量级的 View，它本身不参与绘制，尺寸为 0。只有当调用 `setVisibility(VISIBLE)` 或 `inflate()` 时，ViewStub 才会被替换为实际的布局。首帧时 ViewStub 对应的布局不会被 inflate，减少了首帧的工作量。

```xml
<!-- 首页布局中，错误提示页面只在出错时才显示 -->
<ViewStub
    android:id="@+id/error_page_stub"
    android:layout="@layout/error_page"
    android:layout_width="match_parent"
    android:layout_height="match_parent" />
```

```kotlin
// 需要显示错误页面时才 inflate
val errorPage = binding.errorPageStub.inflate()
errorPage.showError(message)
```

ViewStub 最适合的场景是"大部分时候不会显示的布局"，比如错误页面、空数据页面、引导页面等。这些页面在正常使用中不会出现，如果提前 inflate 就是白白浪费启动时间。

### AsyncLayoutInflater：把 inflate 移到后台线程

对于必须在首帧显示但 inflate 耗时很长的布局，可以考虑使用 `AsyncLayoutInflater`（来自 `androidx.asynclayoutinflater` 库），将 inflate 操作移到后台线程执行：

```kotlin
AsyncLayoutInflater(this).inflate(R.layout.activity_main, null) { view, _, _ ->
    setContentView(view)
    // View 树已经 inflate 完成，可以开始后续初始化
    setupViews()
}
```

AsyncLayoutInflater 的局限性需要了解：

1. **inflate 完成前 Activity 没有 content view**，这段时间窗口是空的（会显示 Starting Window）。所以需要配合 SplashScreen 使用，避免出现白屏。
2. **不能 inflate 包含 `fragment` 标签的布局**——因为 Fragment 的创建需要在主线程上进行。
3. **自定义 View 的构造函数中不能有依赖主线程的操作**（比如获取 Window 参数），因为 inflate 发生在后台线程。
4. **parent 的 generateLayoutParams 方法必须是线程安全的**。

在实际项目中，AsyncLayoutInflater 的收益要用 Perfetto 或 Macrobenchmark 量出来；布局越复杂，收益空间通常越大。

### 布局扁平化：减少嵌套层级

布局嵌套层级直接影响 measure 和 layout 的递归次数。Android Studio 的 Layout Inspector 和 Lint 工具可以帮助发现过深的嵌套。

一些常见的扁平化策略：

- 用 ConstraintLayout 替代多层嵌套的 LinearLayout 和 RelativeLayout。ConstraintLayout 可以用一层布局实现之前需要 2-3 层嵌套才能实现的布局效果。
- 使用 `<merge>` 标签减少不必要的层级。当子布局的根元素可以直接作为父容器的子 View 时，用 `<merge>` 替代根元素，避免多加一层。
- 避免在 LinearLayout 中使用 `weight`——它会触发两次 measure。可以用 ConstraintLayout 的百分比约束或者 Guideline 替代。

## Baseline Profile：让系统提前编译热点代码

[已验证: 来源见 developer.android.com/topic/performance/baselineprofiles]

### 什么是 Baseline Profile

Android 应用的代码在安装后并不会全部编译成机器码。ART 运行时采用的是"解释执行 + JIT 编译 + AOT 编译"的混合策略：首次执行时解释执行，频繁执行的代码（热点代码）会被 JIT 编译器编译成机器码并缓存。在设备空闲时，系统可能会将部分热点代码 AOT 编译。

应用首次启动时，大量代码仍处于"解释执行"状态，执行效率远低于编译后的机器码。对于启动路径上的代码（从 Application.onCreate 到首帧绘制），这种性能损失可能贡献了几百毫秒甚至更多的额外耗时。

Baseline Profile 是一个由开发者随 release 包发布的热点代码规则文件，HRF 文本规则会在构建时转成 `baseline.prof`。它的消费路径要拆开看：Google Play 安装可以在安装阶段用 Baseline Profile 触发 `speed-profile` 编译；非 Play 渠道也可以随 APK 携带 `baseline.prof`，再由 `androidx.profileinstaller` 在首次运行后把 profile 写入设备侧，等待后台 dexopt 或手动 `cmd package compile -m speed-profile -f` 完成编译。

Cloud Profile 是另一条路径：Google Play 收集并聚合真实用户运行时 profile，再把聚合结果用于后续安装或更新。它属于 Play 分发侧能力，和开发者打包进 APK 的 Baseline Profile、ART Mainline 模块更新分属不同层级。

### Baseline Profile 的制作

Android 提供了一套工具链来生成 Baseline Profile：

1. **在 `build.gradle` 中添加依赖**：

```groovy
dependencies {
    implementation("androidx.profileinstaller:profileinstaller:1.4.1")
    testImplementation("androidx.benchmark:benchmark-macro-junit4:1.3.3")
}
```

2. **编写生成 Baseline Profile 的测试用例**：

```kotlin
@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule
    val rule = BaselineProfileRule()

    @Test
    fun generateBaselineProfile() {
        // includeInStartupProfile 需要 benchmark-macro-junit4 1.2.0+
        // true 表示同一条启动路径也写入 Startup Profile
        // 1.3.0+ 还支持 DSL 配置 profile mode
        rule.collect(
            packageName = "com.example.app",
            includeInStartupProfile = true  // benchmark-macro-junit4 1.2.0+
        ) {
            // 这个块定义了需要优化的用户旅程
            // 启动应用
            startActivityAndWait()
            // 等待首页完全加载
            device.waitForIdle()
            // 可以添加更多的用户操作，覆盖更多的热点代码路径
        }
    }
}
```

3. **运行测试生成 Profile 文件**：

生成任务会产出 HRF 规则，常见落点是 `src/<variant>/generated/baselineProfiles/baseline-prof.txt`；开启 Startup Profile 后，还会把启动路径写入 `startup-prof.txt`。两者用途不同：

- `baseline-prof.txt`：描述需要 ART AOT 编译的热点类和方法，最终打包成 `assets/dexopt/baseline.prof`。
- `startup-prof.txt`：服务于 DEX layout。这是构建工具链能力，不是运行时行为——AGP/R8/D8 在构建阶段消费 `startup-prof.txt`，将启动热点类物理集中在 primary DEX 的起始扇区（DEX Layout Optimization）。主要价值是减少启动期加载这些类时的 Page Fault，与 AOT 编译是两条独立的优化路径。如果只用了 Baseline Profile 而没配置 Startup Profile，DEX 布局优化这一层就缺失了。版本要求：AGP 8.1 可通过 `android.experimental.dexLayoutOptimization=true` 手动开启；AGP 8.2 支持模板但 variant 有一定限制；AGP 8.3 起默认开启并支持 distinct Startup Profiles。前提是 release 构建需开启 R8（`isMinifyEnabled=true`），Macrobenchmark 1.2.0+ 提供自动化生成；运行时无需特定 Android 版本要求，优化效果取决于 APK 内 DEX 布局。

HRF 方法规则必须包含 flags、类描述符、完整方法签名和返回类型，例如：

```text
HSPLcom/example/app/MainActivity;->onCreate(Landroid/os/Bundle;)V
HLcom/example/app/network/NetworkSDK;->init(Landroid/content/Context;)V
PLandroidx/recyclerview/widget/RecyclerView;->onMeasure(II)V
Lcom/example/app/Application;
```

`H` 表示 hot，`S` 表示 startup，`P` 表示 post-startup。类规则只写类描述符，例如 `Lcom/example/app/Application;`。

4. **将 Profile 文件打包到 APK/Bundle 中**：

Release 构建会把 Baseline Profile 编译成二进制 ART profile 并打进 APK / AAB。Google Play 可以在安装阶段消费这份 profile；非 Play 安装路径需要确认包内是否带有 `baseline.prof`，以及 `ProfileInstaller` / 后台 dexopt 是否已经把设备端编译状态推进到 `speed-profile`。

### 效果量化

Google 官方数据显示，Baseline Profile 对启动速度的提升效果因应用而异：

- 简单应用（代码量少，启动路径短）：提升 10%-20%
- 中等复杂度应用：提升 20%-40%
- 复杂应用（大量 SDK 初始化，复杂的 View 树）：提升可能超过 40%

具体到毫秒数，一个冷启动 2 秒的应用，启用 Baseline Profile 后可能降到 1.2-1.6 秒。

要验证 Baseline Profile 的实际效果，可以使用 `benchmark-macro-junit4` 库进行对比测试：

```kotlin
@Test
fun startupWithoutBaselineProfile() = benchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(StartupTimingMetric()),
    iterations = 10,
    compilationMode = CompilationMode.None()  // 无编译优化
) {
    startActivityAndWait()
}

@Test
fun startupWithBaselineProfile() = benchmarkRule.measureRepeated(
    packageName = "com.example.app",
    metrics = listOf(StartupTimingMetric()),
    iterations = 10,
    compilationMode = CompilationMode.Partial()  // 使用 Baseline Profile
) {
    startActivityAndWait()
}
```

对比两次测试的 `timeToInitialDisplayMs`（对应 TTID）和 `timeToFullDisplayMs`（对应 TTFD，需要应用中调用了 `reportFullyDrawn()` 才能获取），就是 Baseline Profile 的实际收益。

如果应用尚未调用 `reportFullyDrawn()`，`timeToFullDisplayMs` 的值将与 `timeToInitialDisplayMs` 相同（系统无法区分首帧和完全就绪）。建议在应用首页数据加载完成后调用 `reportFullyDrawn()`，这样监控数据才能真实反映用户感知到的启动完成时间。

### Cloud Profile：无需开发者参与的自动优化

除了开发者随包提供的 Baseline Profile，Google Play 还有 Cloud Profile 机制。当大量用户使用应用后，Play Store 会收集并聚合 ART 运行时 profile，把聚合结果提供给后续安装或更新该应用的用户。

Cloud Profile 依赖 Google Play 分发和足够多的真实用户样本，通常需要数小时到数天才能覆盖新版本。Baseline Profile 可以填这段空窗期，也能覆盖没有 Play Cloud Profile 的安装路径；非 Play 渠道的差异主要在编译触发时机，APK 仍然可以携带 Baseline Profile。

关于 Baseline Profile 的制作流程、Cloud Profile 的分发机制以及与 AutoFDO（Android 16 引入的内核级反馈编译优化）的协同关系，8.7 节（Baseline Profiles 与编译优化实践）和 1.12 节（AutoFDO 反馈导向编译优化）会展开讨论。

[待验证：国内主流应用商店是否提供类似 Google Play Cloud Profile 的云端聚合与安装期编译基础设施。]

## 大型 App 的启动框架设计

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06_wechat_性能优化_如何优雅实现_App_秒开.md + 行业公开资料]

### 从 DAG 到 Task 编排系统

当应用的初始化任务超过 30 个、模块之间有复杂的依赖关系时，简单的 DAG 框架就开始不够用了。大型应用（如淘宝、微信、抖音）通常需要一套完整的启动 Task 编排系统。

这种系统的设计通常包含以下几个方面：

**任务描述符。** 每个初始化任务不再是一个简单的 `Initializer` 接口，而是一个功能丰富的描述符，包含：任务名称、依赖列表、执行线程（主线程/IO 线程/CPU 线程）、优先级、是否阻塞首帧、超时时间等。

**有向无环图构建与拓扑排序。** 在编译期或运行时分析所有任务的依赖关系，构建 DAG，并计算拓扑排序后的执行计划。

**动态调度。** 根据运行时的设备能力（CPU 核心数、内存大小）动态调整并发度。在高端设备上可以 8 路并发，在低端设备上限制为 2-3 路并发，避免 CPU 争用。

**监控与上报。** 记录每个任务的执行耗时、线程信息、是否超时，上报到服务端用于分析启动性能。

**降级机制。** 当某个任务执行失败或超时时，触发降级逻辑（比如跳过该任务、使用默认配置），不影响启动流程继续进行。

### 闲时任务调度

启动框架还需要区分"启动阶段必须完成的任务"和"可以延迟到闲时执行的任务"。闲时任务使用 `JobScheduler` 或 `WorkManager` 在设备空闲时执行，不占用启动时间。

典型的闲时任务包括：数据库预填充、配置文件预加载、缓存预热、非关键配置拉取等。

## 启动速度的线上监控与回归检测

[已验证: 来源见 obsidian/Personal-Knowlodge/source/2026-03-06_wechat_性能优化_如何优雅实现_App_秒开.md]

### 为什么需要线上监控

启动优化不是一次性工作。随着版本迭代、新功能加入、SDK 更新，启动速度很容易"悄悄劣化"。某个版本可能刚优化了 200ms，下一个版本新加一个 SDK 又慢了 300ms——如果没有线上监控，团队可能很晚才发现。

线上监控需要覆盖以下几个维度：

**启动耗时分位数。** 不看平均值（被极端值拉偏），看 P50、P90、P95 的启动耗时。P50 代表"典型用户的体验"，P90 代表"大多数用户的体验"，P95 代表"几乎所有人的体验下限"。

**秒开率。** 定义为"启动耗时小于 1 秒的用户占比"。这个指标直观反映用户感知——如果 80% 的用户在 1 秒内看到首页，说明大部分人的体验是好的。

**分阶段耗时。** 把启动流程拆分为几个阶段（Application 初始化、Activity 创建、布局 inflate、数据加载等），分别统计每个阶段的耗时。当总体耗时上升时，可以快速定位是哪个阶段变慢了。

### 自动化回归检测

在 CI 流水线中集成启动速度测试，可以在代码合并前发现性能回归：

```bash
# 使用 adb am start -W 获取冷启动耗时
adb shell am start -W -n com.example.app/.MainActivity

# 输出示例：
# ThisTime: 1234
# TotalTime: 1567
# WaitTime: 1589
# Complete
```

上面输出中的三个时间含义：`ThisTime` 是本次 Activity 的启动耗时；`TotalTime` 是从系统收到启动请求到首帧绘制完成的耗时，即 **TTID**；`WaitTime` 是调用者（adb）的等待时间，包含 TotalTime 加上前一个 Activity 的 pause 耗时。

注意 `am start -W` 只能量测 TTID，无法量测 TTFD（因为 TTFD 依赖 `reportFullyDrawn()` 的调用）。如果需要 TTFD 数据，需要通过 `benchmark-macro-junit4` 或自建线上监控来采集。

更精确的方式是使用 `benchmark-macro-junit4` 库编写自动化的启动速度测试，在 CI 中运行并对比历史数据。如果新代码导致启动耗时增加了超过阈值（比如 5%），则自动阻断合并并通知开发者。

### 在 Perfetto 中定位启动耗时瓶颈

当线上监控发现启动耗时异常时，需要用 Perfetto 进行深入分析。以下是一个典型的分析流程：

1. 抓取冷启动 Perfetto Trace：`adb shell perfetto -c - --txt <<EOF` 配置包含 `am`, `view`, `sched` 等数据源
2. 在 Trace 中搜索 `BindApplication`，定位到启动开始位置
3. 沿时间轴向右看主线程的活动，找到耗时的代码块
4. 如果看到一大段主线程在运行但不知道在做什么，可以叠加 Method Trace（`Debug.startMethodTracingSampling()`）查看具体的方法调用
5. 关注 `Choreographer#doFrame` 第一次出现的位置——这就是首帧绘制的时刻
6. 对比 `BindApplication` 开始和 `doFrame` 结束的时间差，就是从应用侧可以优化的启动耗时

## 版本演进：Android 13-17 对启动优化的影响

前面的优化策略在不同 Android 版本上的生效条件和细节有所不同。这里按版本梳理关键差异，方便在实际项目中对照。

### SplashScreen 相关变更

- **Android 12（API 31）**：引入 SplashScreen API 和兼容库。这是启动画面行为的分水岭。
- **Android 13（API 33）**：新增 per-app language 功能（`android:localeConfig`）。如果应用声明了多语言支持，SplashScreen 的退出时序可能与语言切换逻辑产生交互——在 `installSplashScreen()` 之前设置好 `LocaleListCompat` 可以避免启动画面的语言闪烁。

### Baseline Profile 与编译优化演进

- **Android 12-13**：Baseline Profile 机制进入稳定使用期。Jetpack `benchmark-macro-junit4` 1.2.0 引入 `includeInStartupProfile`，1.3.0 支持 DSL 配置。
- **Android 14-15**：ART 继续通过 Mainline 模块更新运行时和 dexopt 能力，但公开资料没有把 Cloud Profile 写成由 ART Mainline 直接分发。Cloud Profile 仍按 Google Play 的聚合与分发模型理解。
- **Android 16（API 36）**：AutoFDO（Auto Feedback-Directed Optimization）覆盖到 Android 内核优化，[Google 公开材料](https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html)提到 Pixel 上冷启动提升约 4%、boot time 降低约 1%。AutoFDO 与 Baseline Profile 互补：Baseline Profile 决定哪些 Java/Kotlin 方法进入 ART `speed-profile` 编译，AutoFDO 改善内核和 native binary 的机器码布局、分支预测和内联效果。详细机制见 1.12 节。
- **Android 17（API 37）**：官方行为变更已公开 `android.os.MessageQueue` 的 lock-free 实现，适用于 targetSdk 37+ 的应用。它的目标是减少 missed frames，但依赖反射访问 `MessageQueue` 私有字段/方法的启动监控、消息队列 hook 或性能 SDK 可能失效。启动优化场景下，应优先使用 Perfetto、Macrobenchmark、`reportFullyDrawn()` 等公开观测接口，不把 Looper/MessageQueue 私有实现当成稳定锚点。

### profileable 要求变化

从 Android 15 开始，`android:profileable` 标签（AndroidManifest 中声明）的推荐行为有变化。需要明确：`android:profileable` 主要用于 shell 工具和开发环境的性能分析，**不应用于 Cloud Profile 的数据采集**。

Cloud Profile 的数据采集主要通过 Google Play 服务在用户设备上自动进行，不需要在 AndroidManifest 中声明 profileable。如果应用在 debug 构建中启用了 profiling，仅在开发时通过 `android:profileable="true"` 允许性能数据采集即可。

正确做法：
- Debug 构建中设置 `android:profileable="true"`（用于开发和调试）
- Release 构建中不设置 profileable（Cloud Profile 通过 Play 服务自动收集）
避免混淆 shell 工具用途与 Cloud Profile 机制。

### 各版本与启动相关的重要变化

| 版本 | 新增能力 |
|------|---------|
| Android 12（API 31） | SplashScreen API、启动画面与启动体验规范统一 |
| Android 13（API 33） | Per-app language 对启动流程的影响 |
| Android 15（API 35） | ART Mainline / dexopt 持续演进，Cloud Profile 仍按 Play 聚合分发理解 |
| Android 16（API 36） | 内核 AutoFDO、profileable benchmark 支持增强 |
| Android 17（API 37） | targetSdk 37+ 使用 lock-free `MessageQueue`，私有字段/方法 hook 需迁移到公开观测接口 |

## 总结：启动优化的优先级

面对一个启动慢的应用，建议按以下优先级逐步优化：

1. **延迟/懒加载非必要任务**（优先检查，风险相对低）——先把首帧前不需要的任务移出同步路径
2. **ContentProvider 优化**（排查隐式初始化，合并或移除不必要的 ContentProvider）
3. **布局优化**（ViewStub、布局扁平化、AsyncLayoutInflater）
4. **Splash Screen 配置**（改善用户感知，但不减少实际耗时）
5. **多线程并行初始化框架**（中等收益，但实施成本较高）
6. **Baseline Profile**（需要生成、打包并确认设备端进入 `speed-profile`；非 Play 渠道要核对 `ProfileInstaller` 与后台 dexopt）
7. **线上监控与防劣化体系**（长期保障）

操作原则是：**先度量，再优化，后验证**。没有数据支撑的优化是盲目的，没有线上监控的优化是不可持续的。

## 常见问题与误区

### 误区一："把所有 SDK 都改成异步初始化就好了"

异步初始化不能解决所有启动问题。第一，有些 SDK 之间存在依赖关系（如网络库→登录SDK），简单并行会破坏顺序。第二，过度并发在低端设备上会导致 CPU 争用，反而比串行更慢。第三，某些 SDK 的 init 方法内部操作了 UI 线程元素，异步调用会崩溃。正确做法是先分类（必须同步/可异步/可懒加载），再按依赖关系编排执行顺序。

### 误区二："Splash Screen 能加速启动"

SplashScreen API 改善的是用户感知，不是实际启动耗时。从 BindApplication 到 Choreographer#doFrame 的时间不会因为加了 Splash Screen 而缩短。它的价值在于：让用户在等待期间看到品牌画面而不是白屏，以及通过 KeepOnScreenCondition 让启动画面等到数据就绪再消失，避免首页闪烁。

### 误区三："Baseline Profile 在国内也能用"

Baseline Profile 本身可以用于国内渠道，前提是 release 包里带着 `baseline.prof`，并且应用集成 `androidx.profileinstaller`。差异在编译时机：Google Play 可以在安装阶段消费 Baseline Profile；其他安装器或侧载路径通常由 ProfileInstaller 写入设备侧 profile，再等待后台 `bg-dexopt-job` 完成 `speed-profile` 编译。验证时看 `ProfileVerifier` 或 `dumpsys package dexopt`，不要只看包里是否存在 profile 文件。

Cloud Profile 是 Google Play 的云端聚合分发能力。没有 Play Store 的国内渠道通常拿不到这条路径，但这不影响开发者随包发布 Baseline Profile。

### 误区四："启动优化做一次就够了"

启动优化是持续性工作。每次版本迭代引入新 SDK、新功能模块、新的 ContentProvider，都可能让之前优化过的启动耗时重新恶化。没有线上监控（P50/P90 分位数 + 秒开率）和 CI 自动化回归检测，优化成果会在 2-3 个版本内被消耗殆尽。

## 参考资料

- [Android 官方：App startup time](https://developer.android.com/topic/performance/vitals/launch-time)
- [Android 官方：Splash Screen](https://developer.android.com/guide/topics/ui/splash-screen)
- [Android 官方：Baseline Profiles](https://developer.android.com/topic/performance/baselineprofiles)
- [Android 官方：App Startup Library](https://developer.android.com/topic/libraries/app-startup)
- [AOSP: ActivityThread.java](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/app/ActivityThread.java)（进程启动入口）
- [AOSP: ViewStub.java](https://android.googlesource.com/platform/frameworks/base/+/android-16.0.0_r1/core/java/android/view/ViewStub.java)
- [Google I/O 2022: Improve app startup with Baseline Profiles](https://www.youtube.com/watch?v=NfbYyENDfgo)
- [Android Developers Blog：Boosting Android Performance: Introducing AutoFDO for the Kernel](https://android-developers.googleblog.com/2026/03/BoostingAndroid%20PerformanceIntroducingAutoFDO.html)
