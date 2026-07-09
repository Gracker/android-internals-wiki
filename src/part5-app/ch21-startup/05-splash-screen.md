---
title: "Splash Screen 与感知启动速度"
chapter: "21.5"
section: "21.5"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
confidence: medium
drafted_date: "2026-05-13"
polish_count: 0
sources:
  - type: aosp
    path: "frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/SplashScreenStartingData.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java"
  - type: official
    path: "developer.android.com/develop/ui/views/launch/splash-screen"
  - type: official
    path: "developer.android.com/jetpack/androidx/releases/core#core-splashscreen_1.2.0"
  - type: official
    path: "dl.google.com/dl/android/maven2/androidx/core/core-splashscreen/1.2.0/"
  - type: blog
    path: "obsidian/Personal-Knowlodge/source/2026-03-12_wechat_SplashScreen_优化启动体验_开发者说_DTalk.md"
  - type: clippings
    path: "Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md"
tags: [splash-screen, perceived-performance, skeleton-screen, starting-window, window-background, splashscreen-compat]
related_chapters: ["2.12", "8.3", "21.1"]
created_by: "task2a-content-processing"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-16"
task6_reviewed_date: "2026-06-16"
task6_result: "pass-light-edit"
task6_review_notes: "2026-06-16 Task6 revisiting review: pass-light-edit。四层质检全部通过，写作质量无问题。自动晋升 finalized / ready-to-publish。"
last_task6_at: "2026-07-09T18:14:16+08:00"
task6_review_notes: "2026-06-16 01:xx Task6 revisiting review: pass-light-edit。四层质检全部通过，写作质量无问题。Task9 needs-rework（P0 2/P1 1）已由 Task2B 修复，等待 Task9 复审确认。不自动晋升。"
last_task6_review_log: "logs/review/2026-06-16-01-review.md"
last_task6_at: "2026-07-09T18:14:16+08:00"

task2b_result: fixed
last_task2b_at: "2026-06-16T00:51:53"
task2b_fixed_date: "2026-06-16"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-27
last_verified: "2026-07-09"
last_verified_against: "AOSP android-17.0.0_r1; AndroidX core-splashscreen 1.2.0"
task9_result: "auto-fixed"
task9_state: "reviewed"
task2b_state: "fixed"
task6_state: "revisiting"
pipeline_stage: "task6_pending"
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-07-09"
last_task9_at: "2026-07-09T16:30:36+08:00"
last_task9_autofix_at: "2026-07-09"
last_task9_review_log: "logs/deep-review/2026-07-09-16-deep-review.md"
updated_by: "openclaw-task9"
updated_date: "2026-07-09"
p0: 0
p1: 1
p2: 1
task9_review_notes: "2026-06-16 Task9：needs-rework。P0 2 / P1 1。core-splashscreen API 下限、兼容模式/退出动画、postSplashScreenTheme 崩溃口径需回炉。 | 2026-06-16 01:20 Task9 复审：pass-tech-review。P0/P1 0；P2 2 已写入 suggestions；Task6 已通过且 queue 无 pending，自动晋升 finalized / ready-to-publish。 | 2026-06-16 12:40 Task9：auto-fixed。复核 core-splashscreen 1.2.0 AAR/source，修正 minSdk/API21-22 降级行为、低版本圆形 mask、Perfetto/度量工具名，回 Task6 复审。 | 2026-07-09 16 Task9 deep-review AUTO-FIX：P0 0 / P1 1 / P2 1；AOSP 锚点由 android-15.0.0_r1 重锚到 android-17.0.0_r1，并修正 SplashScreen 动画时长口径；回 Task6 复审。"
---
# Splash Screen 与感知启动速度

冷启动的客观耗时和用户体感之间有一段可操作的空间。系统 Starting Window 在 App 进程完成首帧之前给用户视觉反馈；SplashScreen API（Android 12+）统一了这段反馈的配置方式；骨架屏、预渲染、退出动画则让这段过渡更平滑。本节讲这三层工具怎么用、各自的版本边界和 Perfetto 上的观察点。

关于 Starting Window 的系统侧工作机制（ATMS 决策、Shell starting-surface 组件创建流程、TaskSnapshot 路径），详见 2.12 节。本节聚焦 App 侧的配置、适配和感知优化策略。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 SplashScreen API (Android 12+) 适配
- 🔹 感知启动速度优化：骨架屏、预渲染、动画过渡
- 🔹 启动窗口（Starting Window）机制与自定义

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 启动窗口（Starting Window）机制与自定义

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/StartingSurfaceController.java]

### 系统侧在做什么

冷启动时，Launcher 把点击事件交给 system_server，ATMS 判断目标 App 进程不存在，走冷启动路径。在 fork 进程、初始化运行时、执行 `Application.onCreate()` 这整段时间里，用户的屏幕上没有任何来自 App 的视觉内容。Starting Window 的作用就是在这段空白期给用户一个反馈——它的创建和绘制由系统完成，不依赖 App 进程。

Android 12 之后，Starting Window 的决策和创建分在两侧：ATMS/WMS 判断是否需要 starting surface，`StartingSurfaceController` 生成 starting data；WM Shell 的 starting-surface 组件（`SplashscreenWindowCreator.java` / `StartingSurfaceDrawer.java`）负责创建窗口并挂到对应 Task 上。App 进程完成首帧后，`reportDrawFinished` 信号传回服务端，再由 `removeStartingWindow` 通知 Shell 移除 starting surface。

Perfetto 里要把三段分开看：system_server 侧是 starting data 和 Activity/Task 状态变化；Shell 侧是 starting surface 的创建与绘制；App 侧的 `reportDrawFinished` 标记主窗口首帧完成。不要把 starting surface 的绘制算在 App 进程上。

### Android 12 之前的 windowBackground 方案

Android 12 之前，Starting Window 的外观由 App theme 的 `windowBackground` 决定。开发者通常用一个 layer-list drawable：底层纯色 + 上层居中 Logo，让白屏变成品牌色 + Logo。

```xml
<!-- res/drawable/bg_splash.xml -->
<layer-list xmlns:android="http://schemas.android.com/apk/res/android">
    <item android:drawable="@color/brand_background" />
    <item>
        <bitmap
            android:gravity="center"
            android:src="@drawable/logo" />
    </item>
</layer-list>
```

```xml
<!-- res/values/themes.xml -->
<style name="Theme.App.Splash" parent="Theme.AppCompat.Light.NoActionBar">
    <item name="android:windowBackground">@drawable/bg_splash</item>
    <item name="android:windowFullscreen">true</item>
    <item name="android:windowContentOverlay">@null</item>
</style>
```

这套方案的问题：

1. **OEM 差异**：不同厂商对 Starting Window 的实现有裁剪，部分厂商会替换或忽略自定义 `windowBackground`。
2. **过渡生硬**：Starting Window 消失和 App 首帧出现之间没有动画衔接，视觉上是"品牌页突然跳成 App 内容"。
3. **Android 12+ 行为差异**：不适配 SplashScreen API 的 App 在 Android 12+ 上可能出现闪烁——系统先显示默认 SplashScreen，再切到 App 自定义的 windowBackground，再切到 App 内容，多了一次跳变。

### 自建 SplashActivity 的代价

有些应用通过一个专门的 SplashActivity 来显示启动页，等数据加载完再跳转到主页面。这种方式比 `windowBackground` 更灵活（可以显示进度、加载广告），但代价是多了一次 Activity 启动、窗口切换和可能的 relayout：

- SplashActivity 的 `onCreate` → `setContentView` → 首帧绘制本身就要几百毫秒。
- 从 SplashActivity 跳转到 MainActivity 的 `startActivity` + Activity 生命周期 + `setContentView` + 首帧绘制，又是一轮。
- 两次 Activity 切换在 Perfetto 上表现为两段独立的 `reportDrawFinished`，中间夹着一个 `Activity.onPause` / `Activity.onResume` 周期。

系统 SplashScreen 复用 starting surface 生命周期，不增加 App 侧 Activity 数量。SplashActivity 方案在启动 Trace 里的开销肉眼可见。

## SplashScreen API (Android 12+) 适配

[已验证: 官方文档 developer.android.com/develop/ui/views/launch/splash-screen 及 AOSP android-17.0.0_r1 SplashScreen API 源码]

### 设计思路

SplashScreen API 把启动画面的行为统一交给系统处理：开发者配置样式，系统管理"什么时候显示、什么时候消失"。App 不需要自己创建和管理启动页的 View。

核心组件：

- **`Theme.SplashScreen`**：主题配置，控制 icon、背景色、品牌图片、动画时长。
- **`installSplashScreen()`**：Activity 侧的接入点，必须在 `setContentView()` 之前调用。
- **`KeepOnScreenCondition`**：让启动画面在条件满足前保持显示。
- **`setOnExitAnimationListener`**：自定义退出动画。
- **兼容库** `androidx.core:core-splashscreen`：AAR `minSdkVersion=21`；API 23+ 覆盖接近 Android 12 的启动画面行为，API 21-22 只有背景会在 App 启动前显示，图标要等 App 进程启动后出现。

### 配置步骤

**1. 添加依赖**

```groovy
// build.gradle
implementation "androidx.core:core-splashscreen:1.2.0"
```

`1.2.0` 是当前稳定版（2025-11-05 stable）。本节以 `1.2.0` 为基线：AAR `minSdkVersion=21`，`1.2.0` 系列包含日夜间主题、cutout 和 system bar 相关兼容修复；保守项目最低可用 `1.0.1`，新项目优先验证 `1.2.0+`。

**2. 配置主题**

```xml
<style name="Theme.App.Starting" parent="Theme.SplashScreen">
    <!-- 背景色 -->
    <item name="windowSplashScreenBackground">@color/brand_background</item>
    <!-- 中央图标，支持 AnimatedVectorDrawable -->
    <item name="windowSplashScreenAnimatedIcon">@drawable/splash_icon</item>
    <!-- 图标动画时长，官方建议不超过 1000ms -->
    <item name="windowSplashScreenAnimationDuration">1000</item>
    <!-- 启动画面结束后的 Activity 主题 -->
    <item name="postSplashScreenTheme">@style/Theme.App</item>
</style>
```

`postSplashScreenTheme` 是迁移必填项，必须指向 App 正常运行时使用的主题。SplashScreen 消失后，系统会把 Activity 的主题从 `Theme.App.Starting` 切换到 `postSplashScreenTheme`。缺失时兼容库不会替 Activity 切回正常主题，可能导致启动后主题或窗口属性异常；不存在的资源引用通常在构建期就会失败，不会留到运行时。

**3. 在 Manifest 中设置主题**

```xml
<activity
    android:name=".MainActivity"
    android:theme="@style/Theme.App.Starting"
    android:exported="true">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>
```

主题设置在 Activity 级别（不是 Application 级别），这样只有启动 Activity 走 SplashScreen 路径，其他 Activity 不受影响。

**4. 在 Activity 中安装 SplashScreen**

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        val splashScreen = installSplashScreen()
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
    }
}
```

`installSplashScreen()` 必须在 `super.onCreate()` 之前调用。AndroidX `SplashScreen.kt` 的 Usage 文档明确要求："call installSplashScreen just before super.onCreate()"。代码示例中的顺序已正确。`setContentView()` 放在 `super.onCreate()` 之后即可。

[已验证: AndroidX `core-splashscreen` SplashScreen.kt Usage 段落 — call installSplashScreen() just before super.onCreate()]

### 版本行为差异

| 特性 | Android 5-11 / API 21-30（兼容库模式） | Android 12+ / API 31+（原生 API） |
|------|--------------------------|------------------------|
| 中央图标 | API 21-22 启动前只显示背景；API 23-30 显示静态图标，不支持 AVD 动画 | 支持 AnimatedVectorDrawable 动画 |
| 背景色 | 支持 | 支持 |
| 品牌图片（底部） | 不显示 | `windowSplashScreenBrandingImage` |
| 退出动画 | 由兼容库 SplashScreenViewProvider / dispatchOnExitAnimation 模拟 | `setOnExitAnimationListener` |
| 圆形遮罩 | 兼容库按 Adaptive Icon 尺寸做圆形 mask；API<31 直接传 adaptive icon 可能被裁剪，需拆 foreground/background | 遵循 Adaptive Icon 规范，图标在圆形区域内 |
| Starting Window 创建 | 系统仍可能显示旧 preview/starting window；兼容库的 keep/exit view 在 Activity `DecorView` 内处理，不创建额外 Activity | Shell starting-surface 组件创建 |

[待补充：各 Android 版本上 SplashScreen 外观的截图对比]

### 保持启动画面：KeepOnScreenCondition

默认行为是 App 绘制第一帧后启动画面立即消失。但有些场景需要延迟消失——比如等首页数据加载完成、等开屏广告加载完成。

```kotlin
val splashScreen = installSplashScreen()

var dataReady = false
splashScreen.setKeepOnScreenCondition { !dataReady }

viewModel.homeData.observe(this) { data ->
    dataReady = true
    // 条件变为 false，启动画面在下一次检查时消失
}
```

这个回调每帧都会被检查。回调返回 `true` 时启动画面保持显示，返回 `false` 时启动画面退出。用它替代旧的 `ViewTreeObserver.OnPreDrawListener.addOnPreDrawListener { return false }` 模式——功能和性能特征相同，但代码更直接。

### 退出动画

SplashScreen 消失时可以接一个自定义动画，让启动画面平滑过渡到 App 内容：

```kotlin
splashScreen.setOnExitAnimationListener { provider ->
    val splashView = provider.view
    val slideUp = ObjectAnimator.ofFloat(
        splashView, View.TRANSLATION_Y,
        0f, -splashView.height.toFloat()
    )
    slideUp.interpolator = AnticipateInterpolator()
    slideUp.duration = 200L
    slideUp.doOnEnd { provider.remove() }
    slideUp.start()
}
```

两件事要注意：

1. **必须调用 `provider.remove()`**：动画结束后不调用这个方法，启动画面会一直停留在屏幕上。系统不会自动清理。
2. **动画时长要克制**：退出动画的时间会叠加到启动耗时里。官方示例使用 200ms；实际操作中 200-300ms 已经足够传达过渡感，过长会拖慢体感启动。

[已验证: AOSP android-17.0.0_r1, frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/SplashscreenWindowCreator.java]

### 从旧方案迁移

如果应用之前用 `windowBackground` 或自建 SplashActivity 实现启动页，迁移步骤：

1. 移除旧的 `windowBackground` 自定义主题。
2. 添加 `androidx.core:core-splashscreen` 依赖。
3. 创建 `Theme.SplashScreen` 的子主题，把旧的背景色和 Logo 迁移到 `windowSplashScreenBackground` 和 `windowSplashScreenAnimatedIcon`。
4. 在 Activity 中调用 `installSplashScreen()`。
5. 如果之前有 SplashActivity，把它的数据加载逻辑搬到主 Activity 的 ViewModel 里，用 `KeepOnScreenCondition` 控制启动画面消失时机，然后删掉 SplashActivity。
6. 测试 Android 5-11 / API 21-30 的兼容表现——API 21-22 启动前只有背景可见，API 23-30 显示静态图标；API<31 图标 AVD 动画不可用，退出动画由 provider 模拟。

迁移完成后，Perfetto 上的变化：原来两次 `reportDrawFinished`（SplashActivity + MainActivity）变成一次（MainActivity），中间的 Activity 切换开销消失。

## 感知启动速度优化：骨架屏、预渲染、动画过渡

SplashScreen 解决的是"点击到 App 首帧"这段时间的系统侧反馈。但 SplashScreen 消失之后、App 内容完全加载出来之前，用户可能面对一个半成品的页面——空白的列表、未加载的图片、loading indicator 满天飞。

感知优化要解决的就是这个阶段的问题：让用户在内容加载完成之前就感受到"App 已经准备好了"。

### 骨架屏（Skeleton Screen）

骨架屏在内容区域显示一个与最终布局结构一致的低精度占位——灰色的卡片、圆形的头像、矩形的文字行。用户看到的是一个"正在填充的框架"，而不是空白。

实现方式有两种：

**方式一：布局文件直接写骨架状态**

```xml
<!-- res/layout/item_home_skeleton.xml -->
<LinearLayout
    android:layout_width="match_parent"
    android:layout_height="wrap_content"
    android:orientation="vertical"
    android:padding="16dp">

    <!-- 头像占位 -->
    <View
        android:layout_width="40dp"
        android:layout_height="40dp"
        android:background="@drawable/skeleton_circle" />

    <!-- 标题占位 -->
    <View
        android:layout_width="200dp"
        android:layout_height="16dp"
        android:layout_marginTop="8dp"
        android:background="@drawable/skeleton_rect" />

    <!-- 正文占位 -->
    <View
        android:layout_width="match_parent"
        android:layout_height="12dp"
        android:layout_marginTop="4dp"
        android:background="@drawable/skeleton_rect" />
</LinearLayout>
```

`skeleton_circle` 和 `skeleton_rect` 是带圆角的灰色 drawable，配合 shimmer 动画（从左到右的渐变扫光）给用户"正在加载"的暗示。

**方式二：基于真实布局自动生成骨架**

用 `ShimmerLayout` 或 `SkeletonLayout` 这类库，在真实布局外面套一层，把子 View 的背景替换成灰色占位。这种方式维护成本低——布局改了骨架自动跟着变——但可控性不如方式一。

骨架屏的时机：在 `setContentView` 之后就显示骨架状态，等数据加载完成后再切到真实内容。不要等数据回来才显示任何东西——用户从 SplashScreen 跳到空页面，体验不会比白屏好多少。

### 预渲染策略

预渲染是在 App 进程启动后、用户看到首帧之前，提前把一部分 UI 结构准备好，减少首帧绘制时的 inflate 和 measure 开销。

常见的预渲染场景：

**1. 预 inflate 布局**

在 `Application.onCreate()` 或启动阶段的后台线程里，提前 inflate 首页会用到的布局，缓存到内存里。首页 `setContentView` 时直接用缓存的 View 树，省去 inflate 耗时。

```kotlin
// 在后台线程预 inflate
 Executors.newSingleThreadExecutor().execute {
    val cachedView = LayoutInflater.from(context).inflate(R.layout.activity_main, null)
    layoutCache["activity_main"] = cachedView
}
```

注意：预 inflate 创建的 View 没有挂到 Window 上，后续 `addView` 时还会走一遍 measure/layout。它的收益主要在省掉 XML 解析和反射创建 View 的时间，对复杂布局效果明显，简单布局收益不大。

**2. 预加载数据到内存缓存**

在启动阶段并行发起首页数据请求，数据回来后存到内存缓存。等首页 Fragment/Activity 创建时直接从缓存读，跳过网络等待。

这和"在 SplashActivity 里等数据加载完再跳转"是同一条路，但用 SplashScreen + KeepOnScreenCondition 替代 SplashActivity 后，省掉了 Activity 切换开销。预加载请求在 `Application.onCreate()` 或 `ContentProvider` 里发起（详见 21.2 节启动框架），KeepOnScreenCondition 等数据就位后释放。

**3. Baseline Profile 优化冷启动路径的 JIT 编译**

Android 7+ 的 ART 使用 AOT + JIT 混合编译。冷启动时，首页布局 inflate、ViewModel 初始化、数据解析这些代码路径如果还没被 AOT 编译过，会走解释执行或 JIT 边跑边编译，耗时比编译后的机器码慢 2-5 倍。

Baseline Profile（原 Cloud Profiles）让开发者在 AGP 构建时指定关键代码路径，安装时由系统提前 AOT 编译这些路径。对冷启动的改善幅度在 10-30% 之间，取决于 App 启动路径的复杂度和设备性能。

配置方式：

```kotlin
// build.gradle.kts — Baseline Profile 配置
// AGP 8.1-8.2 需显式开启 dex 布局优化
// AGP 8.3+ 默认启用，无需手动设置
baselineProfile {
    dexLayoutOptimization = true  // AGP 8.1-8.2 需要；AGP 8.3+ 可省略
}
```

Baseline Profile 采集侧使用 `BaselineProfileRule`，关键参数是 `includeInStartupProfile`：

```kotlin
@RunWith(AndroidJUnit4::class)
class BaselineProfileGenerator {
    @get:Rule
    val baselineProfileRule = BaselineProfileRule()

    @Test
    fun generateBaselineProfile() {
        baselineProfileRule.collect(
            packageName = "com.example.app",
            includeInStartupProfile = true  // 标记为启动关键路径
        ) {
            // 启动场景的自动化操作
        }
    }
}
```

[已验证: Android Developers, developer.android.com/topic/performance/baselineprofiles]

### 动画过渡：从启动画面到 App 内容

SplashScreen 的退出动画是系统侧到 App 侧的过渡。App 内容加载完成后，内部的过渡动画（Activity 共享元素过渡、Fragment 过渡、列表项入场动画）则是 App 侧自己的感知优化。

几个实践要点：

1. **Activity 共享元素过渡（Activity Transition）**：从列表页进入详情页时，用 `ActivityOptions.makeSceneTransitionAnimation()` 让点击的卡片"膨胀"成详情页，比默认的左右滑入更连贯。但这个过渡有成本——系统需要在过渡期间同时保持两个 Activity 的 View 树和 Surface，内存和 GPU 负担都会增加。低端设备上如果过渡动画出现掉帧，不如直接用默认过渡。

2. **列表项入场动画**：RecyclerView 的 `ItemAnimator` 默认提供 change/move/add/remove 动画。首页数据加载完成后，列表项从底部逐个滑入的效果比"一瞬间全部出现"更自然。但要注意两点：入场动画期间 RecyclerView 会阻止 item 的 measure/layout 复用，动画时长不宜超过 300ms；`setItemAnimator(null)` 可以完全关闭动画，在不需要入场效果的列表上应该关闭。

3. **页面切换过渡的一致性**：整个 App 的过渡动画风格保持一致——都用底部滑入、都用共享元素、或者都用 fade。混合多种过渡风格会让用户对"返回上一页会怎样"缺乏预期。

### 感知优化的度量维度

| 度量 | 含义 | 采集方式 |
|------|------|----------|
| TTID（Time To Initial Display） | 从点击到 App 首帧完成 | 系统 Trace / Android Vitals |
| TTFD（Time To Fully Drawn） | 从点击到内容完全可交互 | `Activity.reportFullyDrawn()` |
| 感知启动时间 | 用户主观感受的启动耗时 | 用户调研 / A/B 实验留存率 |
| 首帧内容质量 | 首帧展示了多少有效内容（不是骨架屏/空白） | 截图对比 + 自动化检测 |

TTID 和 TTFD 的区别：TTID 是"画了第一帧"的时间，但这一帧可能只是骨架屏。TTFD 是"内容完全可用"的时间——列表数据加载完成、用户可以操作。Android 12+ 如果在系统判定 TTID 之前就调用了 `reportFullyDrawn()`，系统会把这次 TTFD 记成 TTID，避免过早上报把启动耗时做小。

[自动发现] 详见 8.3 节关于 TTID/TTFD 的度量方法论和 Perfetto SQL 查询。

## 常见问题与踩坑

### Android 12+ 的闪烁问题

App 在 Android 12+ 上不适配 SplashScreen API 时，启动流程可能出现闪烁：系统先显示默认 SplashScreen（灰色背景 + App 图标），然后切到 App 的 `windowBackground`，再切到 App 内容。三次跳变。

解决：用 SplashScreen API 替代 `windowBackground` 方案。如果暂时无法迁移，在 theme 里把 `windowBackground` 配成和 SplashScreen 默认外观一致的颜色，减少跳变的视觉冲击。

### 兼容库在低版本上的限制

`androidx.core:core-splashscreen` 的 AAR `minSdkVersion=21`。在 Android 5-11 / API 21-30 上，兼容库读取启动 Activity 的主题并切换到 `postSplashScreenTheme`，用 `OnPreDrawListener` 控制显示时机，用 `SplashScreenViewProvider` 驱动退出动画，不创建额外 Activity。因此：

- API 21-22 启动前只显示背景，图标要等 App 进程启动后出现；API 23-30 显示静态图标。API<31 不支持启动图标 AVD 动画，退出动画由兼容库 overlay / provider 模拟，功能可用。
- `KeepOnScreenCondition` 的行为和 Android 12+ 一致。
- 兼容库模式下的 SplashScreen 不是系统侧 Starting Window，它的绘制发生在 App 进程里，不算系统侧 starting surface。

在 Perfetto 里分析低版本启动时，要区分兼容库创建的 View 和系统 Starting Window——它们在不同的进程和不同的时间段。

### SplashScreen 与 reportFullyDrawn 的关系

`Activity.reportFullyDrawn()` 是上报 TTFD 的信号，它不影响 SplashScreen 的显示时机。SplashScreen 的消失由三个因素决定：

1. App 完成首帧绘制（默认行为）。
2. `KeepOnScreenCondition` 返回 `false`。
3. 退出动画执行完毕并调用了 `provider.remove()`。

`reportFullyDrawn()` 只用于度量上报（Macrobenchmark、Perfetto、Play Console），不参与 SplashScreen 的生命周期管理。把这两者混在一起是常见的误解。

[已验证: 官方文档 developer.android.com/about/versions/12/features/splash-screen 及 Activity.reportFullyDrawn() API 说明]

## Perfetto 观察清单

在 Perfetto 中分析 SplashScreen 相关的启动行为时，关注以下 Slice 和 Counter：

| 观察对象 | Perfetto 关键词 | 位置 |
|----------|----------------|------|
| Starting Window 创建 | `addStartingWindow` | system_server |
| Starting Window 移除 | `removeStartingWindow` | system_server |
| Shell 侧 SplashScreen 绘制 | `SplashscreenWindowCreator` | Shell / SystemUI |
| App 首帧完成 | `reportDrawFinished` | App 进程 |
| SplashScreen 退出动画 | 自定义 ObjectAnimator | App 进程 |
| 兼容库模式下的 View / overlay 创建 | `SplashScreenViewProvider` / 应用侧自定义 trace 标记 | App 进程 |

分析启动耗时时，三段时间对应用户体感的三个阶段：

1. **点击到 Starting Window 显示**：系统侧处理时间，App 无法控制。通常 < 100ms。
2. **Starting Window 显示到 App 首帧完成**：App 冷启动的核心耗时区。这个阶段优化参见 21.1-21.4 节。
3. **App 首帧到内容完全加载**：骨架屏 → 真实内容的过渡时间。用 TTFD - TTID 衡量。
