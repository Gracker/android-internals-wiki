---
title: "Splash Screen 与感知启动速度"
chapter: "21.5"
section: "21.5"
status: finalized
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
confidence: medium
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
last_verified: "2026-07-09"
last_verified_against: "AOSP android-17.0.0_r1; AndroidX core-splashscreen 1.2.0"
task9_state: "reviewed"
task2b_state: "fixed"
task6_state: "reviewed"
pipeline_stage: "ready-to-publish"
---
# Splash Screen 与感知启动速度

用户点击图标之后、App 首帧画出来之前，系统可以做很多事来缩短体感等待时间。Starting Window 在 App 进程就绪前先给视觉反馈；SplashScreen API（Android 12+）把这段反馈统一成可配置样式；骨架屏、预渲染和退出动画再让过渡更平滑。以下说明这三层工具的用法、版本边界和 Perfetto 分析方法。

Starting Window 的系统侧工作机制（ATMS 决策、Shell starting-surface 组件创建流程、TaskSnapshot 路径）详见 2.12 节。这里聚焦 App 侧的配置、适配和感知优化策略。

## 范围

Splash Screen 的价值是尽快给出稳定、连续的视觉反馈。它不能缩短进程创建、主线程初始化、I/O 或首屏布局本身；把启动画面多留几秒，也不会让应用更快。

平台源码锚点为 Android 17 / API 37 / `android-17.0.0_r1`，App 侧兼容实现以 AndroidX `core-splashscreen:1.2.0` 为参考。系统侧 Starting Window 的完整机制见 [WindowManager](../../part1-fundamentals/ch02-rendering/12-window-manager.md)，以下重点说明应用如何配置、迁移、交接内容和验证效果。

## 1. 先区分三种画面

启动期间可能连续出现三类画面：

| 画面 | 创建者 | 出现阶段 | 主要职责 |
| --- | --- | --- | --- |
| starting surface | system_server 与 WM Shell | App 窗口可显示前 | 立即反馈、遮住进程与首帧准备 |
| App 第一帧 | App 主窗口 | TTID | 给出可识别的应用结构 |
| 完整内容 | App 主窗口 | TTFD | 主要内容可见并可交互 |

starting surface 也不总是品牌 Splash。Android 17 可以按启动条件选择：

- Splash Screen；
- 纯色 Splash Screen；
- legacy Splash Screen；
- TaskSnapshot；
- windowless starting surface；
- 不创建 starting window。

TaskSnapshot 常用于已有任务切回前台，Splash 常见于冷启动、新任务或目标 Activity 尚未创建的 warm start。已经存在并可直接显示目标 Activity 的 hot start，不会重复显示 Splash。

因此，“点击图标后看见了一张图”还不足以判断系统走了哪条路径。先确认启动类型和 starting window 类型，再解释 Trace。

## 2. Android 17 的系统链路

### 2.1 system_server 负责条件和数据

Android 17 的 [`ActivityRecord.addStartingWindow()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityRecord.java)先检查：

- 当前显示是否允许创建 starting window；
- App 主窗口是否已经绘制；
- 是否有可用且兼容的 TaskSnapshot；
- 这是新任务、任务切换、进程已运行还是 Activity 已创建；
- 启动主题是否允许 starting window。

选择 Splash 路径后，`ActivityRecord` 创建 `SplashScreenStartingData`。[`SplashScreenStartingData`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/SplashScreenStartingData.java)再调用 [`StartingSurfaceController.createSplashScreenStartingSurface()`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/StartingSurfaceController.java)，通过 TaskOrganizer 把创建请求交给 Shell。

### 2.2 WM Shell 负责类型细化和绘制

下面是 Android 17 上的主要调用关系：

```text
ActivityRecord.addStartingWindow()
  ├─ SnapshotStartingData
  └─ SplashScreenStartingData
       ↓
StartingSurfaceController
       ↓ TaskOrganizer
StartingWindowController
       ↓ StartingWindowTypeAlgorithm
StartingSurfaceDrawer
       ├─ SplashscreenWindowCreator
       ├─ SnapshotWindowCreator
       └─ Windowless*Creator
```

[`PhoneStartingWindowTypeAlgorithm`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/phone/PhoneStartingWindowTypeAlgorithm.java)根据 system_server 传来的参数，在 snapshot、不同 Splash 类型和 none 之间作出建议。[`StartingWindowController`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java)接收 TaskOrganizer 回调，[`StartingSurfaceDrawer`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingSurfaceDrawer.java)再派发给具体 creator。

这条链路说明两个边界：

1. Splash 由系统在 App 第一帧前创建，不需要 App 进程先 inflate 一张启动页。
2. App 主题只是输入之一，最终类型还受任务、进程、snapshot、窗口状态和系统策略影响。

### 2.3 移除与退出动画

当 App 内容可以显示时，system_server 请求 Shell 移除 starting window。若应用注册了 Splash 退出动画，系统可以把 `SplashScreenView` 交给 App 侧继续播放；Android 17 的 [`SplashscreenWindowCreator`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/SplashscreenWindowCreator.java)包含 copy、移除和 surface host 释放路径。

不要把“App 已提交第一帧”“starting window 已移除”“退出动画已完成”视为同一个时间点。自定义动画会在 App 内容已经准备显示后继续覆盖它一段时间。

## 3. AndroidX SplashScreen 接入

### 3.1 版本边界

校验基线采用稳定版 `androidx.core:core-splashscreen:1.2.0`，其边界是：

| 系统版本 | 实现方式 | 重要差异 |
| --- | --- | --- |
| API 21～22 | AndroidX 兼容主题与 App 侧控制 | 支持背景；启动早期没有兼容 Splash 图标 |
| API 23～30 | AndroidX 模拟 Android 12 行为 | 支持静态图标；不支持启动图标 AVD 动画 |
| API 31～37 | 委托平台 SplashScreen API | 系统 Splash、图标动画和平台退出交接 |

兼容库的 `minSdk` 是 21，图标兼容能力从 API 23 开始。测试范围至少要覆盖 API 21/22、23～30、31 和当前目标 API，不能只在 Android 17 模拟器上验收。

### 3.2 添加依赖

下面在应用模块引入当前稳定版：

```kotlin
dependencies {
    implementation("androidx.core:core-splashscreen:1.2.0")
}
```

升级版本时要同时回归浅色/深色主题、状态栏和导航栏、display cutout、退出动画以及低版本图标裁剪。AndroidX 1.2.0 的发布说明包含这些兼容区域的修复。

### 3.3 配置 starting theme

下面的主题给出单色背景、启动图标和启动后的正常主题：

```xml
<!-- res/values/themes.xml -->
<style name="Theme.App.Starting" parent="Theme.SplashScreen">
    <item name="windowSplashScreenBackground">@color/launch_background</item>
    <item name="windowSplashScreenAnimatedIcon">@drawable/ic_splash</item>
    <item name="windowSplashScreenAnimationDuration">600</item>
    <item name="postSplashScreenTheme">@style/Theme.App</item>
</style>
```

这里有四个容易误解的点：

- 背景应是单一、不透明的颜色，并在 `values-night` 提供对应资源；
- 图标会按 adaptive icon 的安全区域裁剪，四周必须保留余量；
- `windowSplashScreenAnimationDuration` 描述图标动画时长，不控制 Splash 在屏幕上停留多久；
- `postSplashScreenTheme` 应指向 Activity 的正常主题。若不使用它，就必须在 `onCreate()` 前自行调用 `setTheme()`，两种方式只能有一套清晰的主题切换责任。

官方设计规范不建议依赖底部 branding image。品牌信息应优先由中央图标、颜色和进入内容后的界面承载。

### 3.4 覆盖每个外部启动入口

下面把 starting theme 配给 launcher Activity：

```xml
<activity
    android:name=".MainActivity"
    android:exported="true"
    android:theme="@style/Theme.App.Starting">
    <intent-filter>
        <action android:name="android.intent.action.MAIN" />
        <category android:name="android.intent.category.LAUNCHER" />
    </intent-filter>
</activity>
```

如果通知、deep link 或 App Link 可以在冷进程中直接启动另一 Activity，该入口也要明确处理主题和 `installSplashScreen()`。只验证桌面图标会漏掉这些路径。

### 3.5 在 `super.onCreate()` 前安装

下面展示启动 Activity 的最小接入顺序：

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        val splashScreen = installSplashScreen()
        super.onCreate(savedInstanceState)

        setContentView(R.layout.activity_main)
    }
}
```

`installSplashScreen()` 必须先于 `super.onCreate()`。AndroidX 会读取 starting theme、切换 `postSplashScreenTheme`，并在不同 API 上安装相应的平台或兼容实现。此处拿到的 `splashScreen` 只在需要保持条件或退出动画时使用。

## 4. `KeepOnScreenCondition` 只等待短时本地状态

### 4.1 回调运行在主线程

`KeepOnScreenCondition.shouldKeepOnScreen()` 会在每次准备绘制 Activity 前于主线程调用。回调必须是一次内存状态读取，不能执行：

- 文件或数据库读取；
- Binder 调用；
- JSON 解析；
- 等锁或 `Future.get()`；
- 网络请求；
- 广告 SDK 初始化。

下面的写法让 ViewModel 异步读取少量本地启动状态，条件回调只读取 `StateFlow.value`：

```kotlin
class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        val splashScreen = installSplashScreen()
        super.onCreate(savedInstanceState)

        splashScreen.setKeepOnScreenCondition {
            viewModel.launchState.value == LaunchState.LoadingLocal
        }

        setContentView(R.layout.activity_main)
    }
}

enum class LaunchState {
    LoadingLocal,
    Ready,
    RecoverableError,
}
```

异步任务必须有失败和超时出口，把 `LoadingLocal` 转成 `Ready` 或 `RecoverableError`。若状态永远不变化，Splash 会一直挡住 Activity。

### 4.2 哪些内容可以等

适合短暂等待的内容通常是：

- 本地主题或账户路由；
- 已缓存的登录态；
- 很小的本地配置；
- 决定首个导航目的地的持久化状态。

网络首页、远程配置、图片、推荐流和广告都没有稳定上界。对这些数据，应尽快显示 App 第一帧，再用缓存、占位或错误态继续加载。官方迁移指南也明确建议：不确定时长的网络加载要退出 Splash 后显示 placeholder。

`KeepOnScreenCondition` 会推迟 Activity 的绘制请求。它适合避免极短的路由闪烁，不适合用来把 TTID 包装成一段品牌动画。

## 5. 退出动画

注册 `setOnExitAnimationListener` 后，应用要负责移除 provider。下面用短淡出连接 Splash 和已准备好的首屏：

```kotlin
splashScreen.setOnExitAnimationListener { provider ->
    provider.view.animate()
        .alpha(0f)
        .setDuration(160L)
        .withEndAction {
            provider.remove()
        }
        .start()
}
```

动画结束路径必须调用 `provider.remove()`，否则 Splash View 会继续覆盖应用。还要处理 Activity 销毁、动画取消和重复进入，确保清理不会遗漏。

退出动画有三条约束：

- 内容首帧必须已经在 Splash 下方稳定，避免退出后立即跳布局；
- 时长要用设备实测决定，不能把 200 ms 或 300 ms 当成通用标准；
- 低端机、动画缩放关闭和无障碍设置下也要有合理行为。

动画只改变画面交接。若主线程仍在执行长任务，动画结束后照样会掉帧或无响应。

## 6. 从旧方案迁移

### 6.1 旧 `windowBackground`

Android 11 及更早版本常用启动主题的 `android:windowBackground` 放置 layer-list。Android 12+ 会为 cold/warm start 应用系统 Splash；旧的复杂 `windowBackground` 可能被系统默认 Splash 替换，外观不再等同于旧设备。

迁移时：

1. 把颜色和图标转到 `Theme.SplashScreen` 属性；
2. 设置 `postSplashScreenTheme`；
3. 给所有冷启动入口调用 `installSplashScreen()`；
4. 在 API 21～37 验证主题、图标、系统栏和切换帧；
5. 删除不再使用的旧 layer-list，避免两套启动视觉继续漂移。

### 6.2 专用 `SplashActivity`

Android 12+ 会先显示系统 Splash，再启动旧 `SplashActivity`，容易出现双 Splash。专用 Activity 还会增加一轮 Activity 生命周期、窗口创建和页面跳转。

优先将路由收进单 Activity 或直接启动目标 Activity。若路由 Activity 暂时不能移除，官方迁移方案允许它保持 Splash、立即跳到下一 Activity 并结束自己；这只是过渡方案，路由必须同步、快速且没有网络等待。

开屏广告属于业务页面，不应伪装成系统 Splash。需要展示时，应在系统 Splash 退出后进入可度量、可跳过、失败可恢复的广告页面。

## 7. Splash 后如何交接内容

### 7.1 首帧要稳定，也要尽快

App 第一帧至少应具备：

- 与最终页面一致的背景和系统栏颜色；
- 稳定的顶部栏、导航和主要内容边界；
- 可识别的缓存内容或占位；
- 明确的加载、空数据和失败状态；
- 不会在数据返回后大幅位移的布局。

骨架屏应贴近最终内容结构。占位项数量、宽高和间距如果与结果差异很大，数据回来时会产生明显 layout shift。

### 7.2 优先显示缓存，再异步刷新

可复用内容的推荐顺序是：

1. 读取有边界的本地快照；
2. 绘制首屏和缓存时间；
3. 发起异步刷新；
4. 以稳定过渡替换变化区域；
5. 保留失败重试入口。

没有缓存时显示骨架或空态，不要让 Splash 等网络。骨架元素不应被无障碍服务当成真实按钮或正文；shimmer 动画也要控制面积和时长，并尊重减少动态效果的偏好。

### 7.3 不要在后台线程普通 inflate View

普通 `LayoutInflater` 和多数 View 构造、主题解析、drawable 状态都按主线程 UI 模型设计。把完整页面放到 worker 线程 inflate，再缓存 View 树并挂到 Activity，可能引入主题错误、线程约束、错误 Context、生命周期泄漏和 LayoutParams 不匹配。

若 Trace 显示 inflate 是主成本，优先：

- 减少层级和首帧节点；
- 用 `ViewStub` 延迟非首屏区域；
- 拆分首帧必需和后续内容；
- 检查自定义 View 构造与资源读取；
- 在适用场景评估受支持的异步 inflate 工具，并针对具体布局验证限制。

可以在后台准备不可变数据、解析结果或图片，但 View 创建和挂载仍应遵守 UI 线程与生命周期边界。

### 7.4 编译与初始化问题另行处理

Splash 不解决 JIT 预热、SDK 初始化或任务依赖。对应方法见：

- [Baseline Profile 实战](./04-baseline-profile-practice.md)；
- [启动任务编排](./02-startup-framework.md)；
- [延迟初始化](./06-lazy-initialization.md)；
- [启动完整路径分析](./01-startup-analysis.md)。

不要给 Baseline Profile 写固定“提升 10%～30%”之类承诺。收益取决于规则覆盖、代码路径、编译状态和瓶颈类型，必须用目标产物与设备测量。

## 8. TTID、TTFD 与感知时间

### 8.1 三个时间不能互换

| 指标 | 结束点 | 能回答的问题 |
| --- | --- | --- |
| starting surface 出现时间 | 用户看见系统反馈 | 点击后是否快速得到视觉响应 |
| TTID | App 第一帧完成 | App 多久开始显示自己的 UI |
| TTFD | App 调用 `reportFullyDrawn()` | 主要内容多久达到可用状态 |

Splash 显示得早，不会自动缩短 TTID。骨架屏可以形成更稳定的第一帧，却不等于内容已可用。TTFD 要等主要内容与交互都就绪后上报。

下面在页面状态达到可用条件后上报 TTFD：

```kotlin
lifecycleScope.launch {
    viewModel.screenState
        .filter { it.primaryContentReady && it.primaryActionsEnabled }
        .first()

    reportFullyDrawn()
}
```

这段代码的“可用”条件要由产品页面定义。若自定义 Splash 退出动画仍遮住内容并阻止交互，也应把动画结束纳入可用条件。

如果在系统检测到 TTID 前调用 `reportFullyDrawn()`，系统会把 TTFD 记为 TTID。这样的数据不能说明异步内容已经完成。

### 8.2 需要同时观察什么

至少同时记录：

- cold/warm/hot 启动类型；
- launcher、deep link、通知等入口；
- TTID 与 TTFD 的 p50/p95；
- Splash 保持时间与退出动画时间；
- 第一帧是内容、缓存、骨架还是空白；
- 首屏 FrameTimeline/Jank；
- 设备档位、刷新率和系统版本；
- 失败、离线、慢网和登录态分支。

感知评价可以补充录屏盲测或受控实验，但不能替代 TTID/TTFD 和 Trace。更长的动画可能让画面更连续，也可能推迟操作；两种结果都要测。

## 9. Perfetto 定位

优先使用 Perfetto 的 Android App Startups 派生区间确定启动边界，再分三侧检查：

| 侧 | 观察内容 |
| --- | --- |
| system_server | Activity/Task 状态、starting window 请求、窗口可见与绘制状态 |
| WM Shell / SystemUI | starting surface 类型、创建、copy、退出与移除 |
| App | `bindApplication`、`ActivityThread`、生命周期、首帧、`reportFullyDrawn()`、自定义动画 |

AOSP 中可以搜索 `addStartingWindow`、`removeStartingWindow`、`SplashscreenWindowCreator` 和 `reportDrawFinished`，但 Perfetto slice 名称会随版本、trace 配置和实现变化。不要把源码方法名当成每台设备都必然存在的 slice。

建议给业务门禁增加短而稳定的自定义 trace：

- `launch.route.local_state`；
- `launch.first_content_model`；
- `launch.primary_content_ready`；
- `launch.splash_exit`。

Trace 解释顺序是：

1. starting surface 是否及时出现，类型是否符合该启动；
2. App 主线程为什么还没有提交第一帧；
3. 第一帧到主要内容可用之间在等什么；
4. 自定义退出动画是否遮住已可用内容；
5. 慢路径来自 CPU、I/O、Binder、锁、调度还是渲染。

更完整的启动度量见 [启动优化策略](../../part2-performance/ch08-responsiveness/03-launch-optimization.md)。

## 10. 检查清单

- [ ] 平台锚点为 Android 17 / API 37 / `android-17.0.0_r1`。
- [ ] 已区分 Splash、TaskSnapshot、windowless 和 none。
- [ ] AndroidX 版本与 APK/AAB 依赖可追溯。
- [ ] API 21/22、23～30、31 和 37 均有启动截图或录屏。
- [ ] 浅色/深色、系统栏、cutout 和图标 mask 已验证。
- [ ] 所有外部启动入口都配置 starting theme 并安装 SplashScreen。
- [ ] `installSplashScreen()` 位于 `super.onCreate()` 之前。
- [ ] `KeepOnScreenCondition` 只读取内存状态，且有失败/超时出口。
- [ ] Splash 不等待网络、广告或无上界任务。
- [ ] 自定义退出动画保证调用 `provider.remove()`。
- [ ] 第一帧、缓存、骨架、失败态之间没有明显布局跳变。
- [ ] 没有在 worker 线程用普通 `LayoutInflater` 构造并缓存 Activity View 树。
- [ ] `reportFullyDrawn()` 对应主要内容可见且可交互。
- [ ] TTID、TTFD、首屏帧和 Splash 覆盖时间分别记录。

## 参考资料

- [Splash screens](https://developer.android.com/develop/ui/views/launch/splash-screen)
- [迁移到 Android 12+ SplashScreen](https://developer.android.com/develop/ui/views/launch/splash-screen/migrate)
- [AndroidX Core release notes](https://developer.android.com/jetpack/androidx/releases/core#core-splashscreen_1.2.0)
- [`KeepOnScreenCondition` API](https://developer.android.com/reference/androidx/core/splashscreen/SplashScreen.KeepOnScreenCondition)
- [App startup time：TTID 与 TTFD](https://developer.android.com/topic/performance/vitals/launch-time)
- [AOSP Android 17 `ActivityRecord`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityRecord.java)
- [AOSP Android 17 `StartingSurfaceController`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/StartingSurfaceController.java)
- [AOSP Android 17 `SplashScreenStartingData`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/SplashScreenStartingData.java)
- [AOSP Android 17 `PhoneStartingWindowTypeAlgorithm`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/phone/PhoneStartingWindowTypeAlgorithm.java)
- [AOSP Android 17 `StartingWindowController`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingWindowController.java)
- [AOSP Android 17 `StartingSurfaceDrawer`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/StartingSurfaceDrawer.java)
- [AOSP Android 17 `SplashscreenWindowCreator`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/SplashscreenWindowCreator.java)
