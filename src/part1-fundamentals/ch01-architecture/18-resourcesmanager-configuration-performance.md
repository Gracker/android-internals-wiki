---
title: ResourcesManager 与 Configuration 变更性能
chapter: '1.18'
section: '1.18'
status: finalized
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 ResourcesManager / ResourcesKey / ConfigurationController / ActivityRecord / ActivityThread / AppCompatRecreateOnConfigChangePolicy / DisplayContent / WindowToken；Android 17 官方行为变更文档
confidence: high
sources:
- type: official
  path: https://developer.android.com/guide/topics/resources/runtime-changes
- type: official
  path: https://developer.android.com/guide/topics/manifest/activity-element#config
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored
- type: official
  path: https://developer.android.com/develop/ui/compose/state-saving
- type: aosp
  path: frameworks/base/core/java/android/app/ResourcesManager.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/res/ResourcesKey.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/res/Resources.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/content/res/ResourcesImpl.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/ConfigurationController.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/servertransaction/ActivityRelaunchItem.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/java/android/app/servertransaction/ActivityConfigurationChangeItem.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/AppCompatRecreateOnConfigChangePolicy.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/DisplayContent.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/wm/WindowToken.java @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/core/res/res/values/attrs_manifest.xml @ android-17.0.0_r1
- type: aosp
  path: frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1
tags:
- resources
- configuration
- activity-recreation
- performance
- resourcesmanager
- configChanges
- edge-to-edge
related_chapters:
- '1.12'
- '1.19'
- '8.2'
- '18.1'
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_consolidated_at: '2026-08-11'
consolidated_from:
- src/part1-fundamentals/ch01-architecture/1.48-Android-17-ResourcesManager-Configuration-Activity-Relaunch-判定模型.md
---

# ResourcesManager 与 Configuration 变更性能

一次旋转、折叠展开、窗口缩放或语言切换，应用可能只收到 `onConfigurationChanged()`，也可能销毁并重建 Activity。两条路径都会更新资源，性能成本却完全不同。

排查这类问题时，应依次确认 `Configuration` 中哪些配置位发生变化、`system_server` 选择热派发还是重新启动 Activity（relaunch），再检查资源更新、状态恢复和首帧。这里的 relaunch 是销毁旧 Activity 实例并创建新实例，通常不会重启整个应用进程。Android 17 还改变了部分配置项的默认重建策略，旧版本经验不能直接套用。

当前源码锚点为 Android 17 / API 37 / AOSP `android-17.0.0_r1`，同时说明 Android 12–16 的演进边界。

## 一次 Configuration 变更经过哪些模块

系统级 `Configuration` 更新和单个 Activity 的覆盖配置（override Configuration）最终会在 `ActivityRecord.ensureActivityConfiguration()` 汇合。覆盖配置是窗口容器或 Activity 在全局配置之上叠加的局部值。主路径如下：

```text
全局设置变化                              窗口 / display 层级变化
locale / fontScale / uiMode               rotation / multi-window / foldable bounds
  ↓                                         ↓
ActivityManagerService.updateConfiguration()  DisplayContent / Task / ActivityRecord
  └─ ActivityTaskManagerService                的 ConfigurationContainer 更新
       └─ updateGlobalConfigurationLocked()             │
            ├─ WindowProcessController                  │
            │    └─ ConfigurationChangeItem             │
            │         └─ ConfigurationController        │
            │              └─ ResourcesManager          │
            │                   .applyConfigurationToResources()
            └─ RootWindowContainer / display 层级 ──────────┘
                                      ↓
                 ActivityRecord 的 merged Configuration
                                      ↓
                 ensureActivityConfiguration()
                   ├─ shouldRelaunchLocked() == true
                   │    └─ ActivityRelaunchItem
                   │         └─ ActivityThread.handleRelaunchActivity()
                   └─ shouldRelaunchLocked() == false
                        └─ ActivityConfigurationChangeItem
                             └─ ActivityThread.handleActivityConfigurationChanged()
```

这张图需要区分两个分支：

- **进程级配置**：`ConfigurationChangeItem` 更新应用进程的全局资源和组件回调。
- **Activity 级配置**：`ActivityRecord` 根据变化位、应用清单和兼容策略决定是否 relaunch；不重建时，则把新的合并后覆盖配置热派发给现有 Activity。

多窗口 Activity 收到的不是一份孤立的全局配置。服务端会把全局 `Configuration` 与 Activity 的覆盖配置合并后再下发，这就是合并后配置（merged Configuration）。其中的窗口大小、`displayId`、旋转方向和应用边界都可能来自 Activity 所在的容器。relaunch 路径还会在创建新 Activity 实例前应用待处理的进程配置，避免新实例读取旧资源。

## Resources、ResourcesImpl 与 AssetManager

应用看到的资源对象分三层：

```text
Resources
  └─ ResourcesImpl
       └─ AssetManager
            └─ ApkAssets：base APK、split、overlay、shared library
```

- `Resources` 是公开 API 的包装层，也保存类加载器（ClassLoader）等调用上下文。
- `ResourcesImpl` 保存当前 `Configuration`、`DisplayMetrics`（显示指标）、资源缓存和 `AssetManager`。
- `AssetManager` 管理基础 APK、split APK、资源覆盖包（overlay）和共享库的资源表与原生对象。

多个 `Resources` 可以指向同一个 `ResourcesImpl`。因此，看到多个 `Context` 或 `Resources` 对象，不能据此认定原生资源表被完整复制了多份。

### ResourcesKey 保存什么

Android 17 的 `ResourcesKey` 包含：

| 字段 | 用途 |
|---|---|
| `mResDir`、`mSplitResDirs` | 基础 APK 与 split APK 资源路径 |
| `mOverlayPaths`、`mLibDirs` | 运行时资源覆盖包（RRO）与共享库资源路径 |
| `mDisplayId` | 覆盖默认显示屏的资源目标 |
| `mOverrideConfiguration` | 叠加到全局配置之上的覆盖配置 |
| `mCompatInfo` | 屏幕与密度兼容参数 |
| `mLoaders` | 动态 `ResourcesLoader` 集合 |

全局 `orientation`、`locale`、`screenWidthDp` 不会每次都直接复制进资源键（key）。`mOverrideConfiguration` 只保存相对全局配置的覆盖值。这个区别决定了缓存行为：全局 `Configuration` 改变时，系统通常更新现有 `ResourcesImpl`；显示屏、Activity 覆盖配置、资源路径或 `ResourcesLoader` 组合不同时，才需要不同的资源键。

### 全局配置更新会遍历现有 ResourcesImpl

`ResourcesManager.applyConfigurationToResources()` 的 Android 17 行为：

1. 用 `mResConfiguration.isOtherSeqNewer(config)` 检查配置序号；没有更新且 compat 不变时直接返回。
2. `mResConfiguration.updateFrom(config)` 更新进程级基准配置。
3. 遍历 `mResourceImpls`，把全局配置与每个资源键的覆盖配置合并。
4. 调用 `ResourcesImpl.updateConfiguration()` 更新资源选择、显示指标和内部缓存。
5. Activity 覆盖配置、资源路径或显示屏发生变化并需要不同实现时，通过 `redirectResourcesToNewImplLocked()` 让现有 `Resources` 改指向新的 `ResourcesImpl`。

源码提供的稳定系统轨迹名称是：

```text
ResourcesManager#applyConfigurationToResources
```

“旋转一次就创建一个新 `ResourcesImpl`”和“拖动窗口时为每个尺寸都保留一份缓存”这两种推断都不成立。是否新建取决于资源键和覆盖配置是否改变，以及旧 `ResourcesImpl` 能否复用。

## Activity 为什么会重新启动

`ActivityRecord.shouldRelaunchLocked()` 的最终判断可以写成一个位运算：

```text
(changes & ~skipRelaunchConfigMask) != 0
```

`changes` 是新旧合并后配置的差异位，每一位对应一类配置变化。`skipRelaunchConfigMask` 是位掩码，表示 Activity 或系统策略能够热处理、无需重建的变化。Android 17 按以下来源逐步构造这个掩码：

1. `ActivityInfo.getRealConfigChanged()`：应用清单中的 `android:configChanges`，加上旧目标 SDK 版本的兼容位。
2. `CONFIG_RESOURCES_UNUSED`：Activity 声明不使用资源时跳过重建。
3. 旧 VR 应用的 `uiMode` 兼容规则。
4. 桌面模式（desk mode）切换且应用没有对应桌面模式资源时的跳过规则。
5. 画中画（PiP）中的密度变化。
6. 显示兼容策略，例如尺寸兼容模式。
7. 资源覆盖策略对 `CONFIG_ASSETS_PATHS` 的处理。
8. `AppCompatRecreateOnConfigChangePolicy.getRecreateConfigMask()`：包内存在相应限定符资源，或应用明确要求重建时，把这些位从免重建掩码中移除。

只要还有一个变化位未被免重建掩码覆盖，Activity 就会 relaunch。`orientation` 经常和 `screenSize`、`screenLayout`、窗口边界一起变化，所以只声明 `orientation` 仍可能重建。

### 应用进程内的重建顺序

`ActivityRelaunchItem.execute()` 在应用进程里建立名为 `activityRestart` 的系统轨迹区间，然后调用 `ActivityThread.handleRelaunchActivity()`。后者先应用待处理的进程级 `Configuration`，再进入 `handleRelaunchActivityInner()`：

```text
必要时 onPause
  → onStop，并保存实例状态
  → onDestroy
  → 使用新 Configuration 启动新 Activity 实例
       → onCreate
       → onStart
       → 状态恢复
       → onResume
       → 新 View / Composition 首帧
```

重建成本来自应用生命周期代码、状态保存、布局或 Compose 组合树（Composition）重建、资源冷缓存和新窗口首帧。它不等同于一次冷启动：进程通常还活着，`Application`、进程级单例、代码页和许多缓存仍可复用；但初始化很重的 Activity 也可能比普通热启动更慢。

## Android 17 减少了哪些 Activity 重建

Android 17 默认不再因为以下变化重建 Activity：

- `CONFIG_KEYBOARD`
- `CONFIG_KEYBOARD_HIDDEN`
- `CONFIG_NAVIGATION`
- `CONFIG_TOUCHSCREEN`
- `CONFIG_COLOR_MODE`
- `CONFIG_UI_MODE` 从桌面模式切入或切出，且应用没有对应桌面模式资源时

前五项由 `SKIP_ACTIVITY_RECREATION_ON_CONFIG_CHANGE` 与 `AppCompatRecreateOnConfigChangePolicy` 处理。策略还会扫描包内的 `Configuration` 资源限定符；包内存在相应资源时，系统仍可把该变化放回重建掩码。

依赖旧重建行为刷新界面的 Activity，可以在应用清单中明确声明 `android:recreateOnConfigChanges`：

```xml
<activity
    android:name=".InputActivity"
    android:recreateOnConfigChanges="keyboard|keyboardHidden|navigation|touchscreen|colorMode" />
```

同一配置位同时出现在 `configChanges` 和 `recreateOnConfigChanges` 时，以“不重建、由 Activity 处理”为结果。代码审查时应避免这种自相矛盾的声明。

这项 Android 17 变化不包含 `locale`、`layoutDirection`、`screenSize`、`smallestScreenSize`、`density`、普通夜间模式或字体缩放。它们仍由应用清单、资源限定符和 `shouldRelaunchLocked()` 的其他策略决定。

## configChanges 应该怎样用

`android:configChanges` 把资源和界面更新责任交给 Activity。系统仍会更新 `Configuration`，也仍会调用 `onConfigurationChanged()`；省掉的是 Activity 销毁与重建。

一个只准备自行处理旋转和窗口尺寸的 Activity，可以使用窄声明：

```xml
<activity
    android:name=".PlayerActivity"
    android:configChanges="orientation|screenSize" />
```

对应的回调只处理这两类变化，并在新配置下更新播放器布局：

```kotlin
override fun onConfigurationChanged(newConfig: Configuration) {
    super.onConfigurationChanged(newConfig)
    updatePlayerLayout(
        widthDp = newConfig.screenWidthDp,
        heightDp = newConfig.screenHeightDp,
        orientation = newConfig.orientation,
    )
}
```

回调执行时，Activity 的 `Resources` 已切到新配置。应用需要更新所有受影响对象，包括自定义 View、播放器或相机变换、窗口内边距（insets）、缓存的尺寸、语言文本和嵌入组件。只调用 `super` 不能完成这些工作。

不建议为了性能把 `orientation|screenSize|screenLayout|smallestScreenSize|uiMode|locale|layoutDirection|density` 全部塞进应用清单。每多接管一项，就多一类资源、第三方组件和状态需要人工刷新。默认重建能自动重新选择 `layout-land`、`values-night`、`values-sw600dp`、本地化字符串和不同密度资源，正确性成本通常更低。

选择标准很直接：

- 页面依赖大量限定符资源，或包含难以热更新的 View/Fragment：保留默认重建，优化状态恢复和初始化。
- 播放、相机、游戏或连续窗口动画不能中断，而且团队能维护完整更新逻辑：声明必要的 `configChanges`。
- 只为躲避某个卡顿而接管所有变化：先修 Activity 初始化和状态模型。

## FixedRotation 处理旋转期间的窗口过渡

FixedRotation 会给 `WindowToken` 建立一组模拟旋转后的 `DisplayInfo`、`DisplayFrames` 和 `Configuration`，让窗口在显示屏完成物理旋转前，先按目标方向布局和绘制。Android 17 中常见入口包括：

```text
DisplayContent.handleTopActivityLaunchingInDifferentOrientation()
  → setFixedRotationLaunchingApp()
     → startFixedRotationTransform()
        → WindowToken.applyFixedRotationTransform()
           → WindowToken.onFixedRotationStatePrepared()
```

系统也能对非顶部但可见、方向不同的 Activity 调用 `applyFixedRotationForNonTopVisibleActivityIfNeeded()`。

FixedRotation 不是“禁止 Activity 重建”的开关。`ActivityRecord.applyFixedRotationTransform()` 仍会调用 `ensureActivityConfiguration()`，后续是否 relaunch 继续由配置差异和 `shouldRelaunchLocked()` 决定。它主要处理旋转期间的窗口配置与 Surface 画面变换，减少画面跳变。

默认 Perfetto 系统轨迹中不一定有 `applyFixedRotationTransform` 这类 Java 方法区间。轨迹里没有 `activityRestart`，只能证明 Activity 没有重建，不能反推 FixedRotation 一定参与。判断 FixedRotation 需要结合 WindowManager 日志、窗口状态和对应源码分支。

## Perfetto：区分热更新和 Activity 重建

Android 17 源码中可以直接依赖的系统轨迹区间（slice）名称如下：

| 区间名称 | 位置 | 说明 |
|---|---|---|
| `configChanged` | `ConfigurationController` | 进程级 Configuration 更新 |
| `ResourcesManager#applyConfigurationToResources` | `ResourcesManager` | 更新进程内 ResourcesImpl |
| `activityConfigChanged` | `ActivityConfigurationChangeItem` | Activity 热派发 |
| `activityRestart` | `ActivityRelaunchItem` | Activity 重建 |
| `performCreate:<Activity>` 等 | `Activity` | 新实例的生命周期阶段 |
| `inflate` | `LayoutInflater` | XML View 树构建 |
| `measure`、`layout`、`draw-VRI[...]` | `ViewRootImpl` | View 首帧遍历 |
| `Choreographer#doFrame <vsyncId>` | `Choreographer` | 应用帧执行 |

常见排查方式会搜索 `handleRelaunchActivity` 或 `handleConfigurationChanged`。方法名存在，不代表源码建立了同名系统轨迹区间。Android 17 判断 Activity 是否重建，应优先查 `activityRestart`；判断是否热派发，则查 `activityConfigChanged` 和 `configChanged`。

下面的 SQL 用于列出配置变化附近的稳定区间。`performCreate:` 和 `Choreographer#doFrame` 带动态后缀，所以使用 `GLOB` 匹配：

```sql
SELECT
  p.name AS process_name,
  th.name AS thread_name,
  s.name,
  s.ts / 1e9 AS ts_s,
  s.dur / 1e6 AS dur_ms
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread th USING (utid)
LEFT JOIN process p USING (upid)
WHERE s.name IN (
    'configChanged',
    'ResourcesManager#applyConfigurationToResources',
    'activityConfigChanged',
    'activityRestart',
    'inflate',
    'measure',
    'layout'
  )
  OR s.name GLOB 'performCreate:*'
  OR s.name GLOB 'performStart:*'
  OR s.name GLOB 'performResume:*'
  OR s.name GLOB 'draw-VRI*'
  OR s.name GLOB 'Choreographer#doFrame *'
ORDER BY s.ts;
```

如果应用自己的 `onConfigurationChanged()`、状态恢复或页面初始化没有系统轨迹区间，可以给关键代码添加自定义标记（marker）：

```kotlin
Trace.beginSection("Cfg:updatePlayerLayout")
try {
    updatePlayerLayoutForCurrentWindow()
} finally {
    Trace.endSection()
}
```

采集 Perfetto 后，可以用 `Cfg:updatePlayerLayout` 定位这段应用代码的耗时。

最后用 FrameTimeline 判断用户是否看到卡顿帧，避免只看某个函数的 CPU 时间：

```sql
SELECT
  ts / 1e9 AS ts_s,
  dur / 1e6 AS frame_ms,
  jank_type
FROM actual_frame_timeline_slice
WHERE ts BETWEEN <start_ns> AND <end_ns>
ORDER BY ts;
```

采集时至少记录设备、系统构建指纹、刷新率、Activity、触发方式、是否重建、变化位和样本次数。重建与热更新的对比必须使用同一页面、同一窗口状态和相同数据集，并报告中位数 P50 与尾部值 P95，不能引用缺少测试条件的“快 5–10 倍”。

### 性能归因顺序

1. 有 `activityRestart`：查看 `performStop`、`performDestroy`、`performCreate`、`inflate` 和新窗口首帧。
2. 只有 `activityConfigChanged`：查看应用回调、自定义标记和 `measure` / `layout` / `draw`。
3. `ResourcesManager#applyConfigurationToResources` 很长：检查资源路径、资源覆盖包、多个存活的 `ResourcesImpl` 和资源缓存失效。
4. 各区间都短但 FrameTimeline 仍有卡顿帧：检查主线程调度延迟、渲染线程（RenderThread）、GPU 和 Surface 或窗口过渡。
5. `Configuration` 在短时间内连续变化：按每次事件的配置与窗口边界分组，确认应用是否重复执行网络、解码、数据库或大对象构建。

## 多窗口与折叠屏的连续变化

折叠、展开、跨显示屏和拖动自由窗口时，一次用户操作可能产生多次合并后配置。AOSP 不规定不同厂商必须以相同顺序更新尺寸、密度、旋转方向与窗口形态（posture），应用应把每次回调当作当前有效状态。

处理原则：

- 尺寸和布局更新要轻量，使用当前窗口指标（window metrics）或新 `Configuration` 重新计算。
- 网络请求、图片解码、数据聚合等昂贵工作与尺寸回调解耦；同一任务可取消或复用。
- 需要按帧合并重复 UI 工作时，可以用 `postOnAnimation`、Compose 状态去重或可取消协程，但执行时重新读取最新窗口状态。
- 不要用“宽度变化小于 50dp 就丢弃”这类固定阈值。小变化也可能跨过资源断点、改变文字换行、窗口内边距或相机裁剪。
- 不要等待一个不存在的“窗口缩放手势结束”平台回调后才更新界面；拖动过程中用户也需要看到正确布局。

Jetpack WindowManager 的 `WindowInfoTracker` 用于观察折叠特征和窗口布局信息；`Configuration` 仍负责资源限定符与 Activity 重建。两个信号描述的对象不同，不能互相替代。

## Android 17 的大屏方向与可调整大小策略

Android 16 已开始在大屏上忽略部分方向、宽高比和可调整大小限制，并提供临时退出选项。应用的目标 SDK 升到 Android 17 / API 37 后，这个退出选项不再可用。

在官方定义的大屏边界上，以下 Manifest 属性和运行时 API 可能被忽略：

- `screenOrientation`
- `resizeableActivity`
- `minAspectRatio`、`maxAspectRatio`
- `setRequestedOrientation()`、`getRequestedOrientation()` 对固定横竖屏值的请求

Android 17 文档列出的例外包括：`android:appCategory` 标记的游戏、用户在设备宽高比设置中明确选择应用默认行为，以及最小宽度小于 600dp（sw600dp）的屏幕。

固定竖屏或 `resizeableActivity="false"` 已不能用来避免 `Configuration` 变化。目标 SDK 37 的大屏测试至少覆盖：

- 横屏、竖屏和旋转中的状态保存；
- 分屏与桌面自由窗口的连续缩放；
- 折叠态与展开态；
- 相机预览、视频画面和自定义 Surface 的宽高比与旋转；
- 窗口从一个显示屏移到密度或旋转方向不同的另一个显示屏。

可以在测试设备上启用 `UNIVERSAL_RESIZABLE_BY_DEFAULT` 兼容性开关，提前观察限制被忽略后的行为。测试结果仍要以目标版本、设备窗口模式和官方例外为准。

## Android 17 的 IME 可见性变化

Android 17 中，应用没有自行处理 `Configuration` 变化、因而发生 Activity 重建时，系统不再恢复变化前的输入法（IME）可见状态。页面若要求重建后继续显示键盘，需要明确请求：

- 对适合始终显示键盘的页面设置 `android:windowSoftInputMode="stateAlwaysVisible"`。
- 在新 Activity 的 `onCreate()` 完成输入框创建和焦点恢复后请求显示 IME。
- Activity 自行处理配置变化时，在 `onConfigurationChanged()` 中按业务状态决定是否保持或请求 IME。

不要无条件调用 `showSoftInput()`。输入框尚未附着到窗口、窗口没有焦点，或输入焦点已转移时，请求可能无效，也可能把键盘错误地弹到不再需要输入的页面。

## Compose 与 View 的状态边界

### Compose

读取 `LocalConfiguration.current` 的 Composable 会在配置变化时重新组合。这里的重新组合只更新 Compose UI 树；它与销毁、重建整个 Activity 不是同一件事。各类状态能否保留，取决于 Activity 是否 relaunch：

| 边界 | `remember` | `rememberSaveable` | `ViewModel` | `SavedStateHandle` |
|---|---|---|---|---|
| 同一组合树内重组 | 保留 | 保留 | 保留 | 保留 |
| Activity 重建 | 丢失 | 从 `Bundle` 恢复 | 同一进程内保留原实例 | 可恢复小型 UI 状态 |
| 系统回收进程后重建 | 丢失 | 可从已保存实例状态恢复 | 原实例丢失 | 新 ViewModel 可恢复小型 UI 状态 |

`rememberSaveable` 和 `SavedStateHandle` 都通过 `Bundle` 保存状态，适合保存 ID、筛选项、输入文本和滚动位置；大型列表、位图（Bitmap）或完整页面模型应保存在数据层，并用稳定 ID 重建。

Activity 自行处理 `Configuration` 时，Compose UI 可以通过 `LocalConfiguration` 更新；嵌入的 `AndroidView` 和 Fragment 不会因为 Compose 重组而自动重建。它们原本依赖 Activity 重建来刷新资源和内部状态，因此需要应用明确更新。

### View 与 Fragment

View 页面保留默认重建时，ViewModel 负责同一进程内的页面数据，已保存实例状态机制保存小型 UI 状态。新 Activity 会重新加载限定符资源和 View 树。

自行处理 Configuration 时，检查清单至少包括：

- 使用新的 `Resources` 刷新字符串、颜色、Drawable 和主题相关值；
- 根据新的窗口边界更新布局参数；
- 更新 Fragment 或自定义 View 中缓存的 density、方向和尺寸；
- 重新计算相机、视频、OpenGL/Vulkan Surface 的变换；
- 重新读取窗口内边距，不复用旧的矩形边界对象（`Rect`）；
- 取消以旧尺寸启动、尚未完成的异步工作。

## createConfigurationContext 的使用边界

`Context.createConfigurationContext(override)` 会创建带覆盖配置的 `Context`，适合局部资源查询、预览或隔离的显示环境。下面的示例只用这个 Context 读取中文资源：

```kotlin
val override = Configuration(baseContext.resources.configuration).apply {
    setLocales(LocaleList.forLanguageTags("zh-CN"))
}
val localizedContext = baseContext.createConfigurationContext(override)
val title = localizedContext.getString(R.string.title)
```

应用级语言优先使用 `LocaleManager.setApplicationLocales()` 或 AndroidX `AppCompatDelegate.setApplicationLocales()`。手工创建 `Context` 不会替应用完成 Activity、Service、通知和 Compose 的整体语言切换。

缓存大量带不同覆盖配置的 `Context`，会让 `ResourcesManager` 同时维护更多资源键与 `ResourcesImpl` 组合。临时 `Context` 用完即释放，不要为每次绑定 View 创建一份并长期存入单例。

## Resources 内存诊断

Android 17 的 `mResourceImpls` 是 `ResourcesKey → WeakReference<ResourcesImpl>`。`Resources` 列表和 Activity 关联资源同样以弱引用保存；Activity token 映射使用 `WeakHashMap`。弱引用不会阻止垃圾回收，因此这些缓存容器本身不会强行延长 `ResourcesImpl` 的生命周期。

`resourcesManagerCacheLeakCleanup()` 功能开关启用时，`ReferenceQueue` 负责及时移除失效的键；全局配置更新也会删除已经失效的弱引用。开关未启用时，指向失效弱引用的键可能暂留在映射表中，但对应的 `ResourcesImpl` 已可被垃圾回收。映射表项仍存在，不等于原生对象仍存活。

Android 17 内部有 `ActivityManagerService.dumpResources()` / `dumpAllResources()`，客户端最终调用 `Resources.dumpHistory()`。这组接口按底层 `ApkAssets` 去重后输出资源历史和资源文件，但 `android-17.0.0_r1` 没有提供稳定、公开的 `dumpsys activity resources <process>` 子命令。即使厂商调试工具暴露了内部转储，也不能把输出项数直接解释为 `ResourcesKey` 数量；输出同样不提供“最近创建时间”。

通用工具先看进程内存，再对 debuggable 进程抓堆：

```bash
adb shell dumpsys meminfo <package-name>
adb shell am dumpheap <process-name> /data/local/tmp/app.hprof
```

`am dumpheap` 受应用是否可调试、权限和设备策略限制。原生 `AssetManager` 或资源表分配要用 Perfetto 原生堆分析器；Java HPROF 看不到全部原生内存成本。

资源相关内存持续增长时，按证据逐层确认：

1. 多次执行相同的旋转、语言切换或窗口缩放，观察进程的 PSS（按共享比例计入的进程内存）和原生堆是否在垃圾回收后持续增长。
2. 用 Java 堆转储查看仍存活的 `Resources`、`Context`、Activity 与 `ResourcesImpl`，沿垃圾回收根（GC Root）查找强引用。
3. 用原生堆分析器检查 `AssetManager` 和资源相关分配，不能按 Java 对象数量估算每个 `ResourcesImpl` 的内存。
4. 在可调用内部资源转储的工程环境中对照 `ApkAssets` 路径，确认是否反复加载不同的 split APK、资源覆盖包、共享库或动态 `ResourcesLoader`；量产环境没有该入口时，从堆与加载日志取证。
5. 若只有失效弱引用的资源键数量增加、堆内存没有增长，不应定性为资源泄漏。

静态持有旧 Activity `Context`、长期保存带局部覆盖配置的 `Context`、没有释放主题或插件资源，都会让旧资源对象继续存活。单独看到多个 `ResourcesImpl` 仍不足以下结论；多个显示屏、多个窗口和不同覆盖配置本来就可能需要多个实现。

## 一套可执行的排查流程

### 1. 确认变化位和 Activity 结果

- 记录新旧 `Configuration` 的 `locale`、`uiMode`、`density`、`orientation`、`screenWidthDp`、`screenHeightDp`、`smallestScreenWidthDp` 和窗口边界。
- 在 `onCreate()`、`onDestroy()`、`onConfigurationChanged()` 加带 Activity 实例标识的日志。
- 检查应用清单中的 `configChanges`、`recreateOnConfigChanges`、方向和窗口调整设置。

### 2. 用系统轨迹判断走了哪条分支

- `activityRestart` 存在：分析 Activity 重建生命周期与新窗口首帧。
- `activityConfigChanged` 存在且没有 `activityRestart`：分析热更新回调和 View/Compose 重排。
- 两者都没有：检查系统轨迹是否覆盖目标进程、`atrace` 类别和正确的时间窗口。

### 3. 把系统成本与应用成本分开

- `ResourcesManager#applyConfigurationToResources`：Android 框架的资源更新。
- 应用自定义标记：业务回调、数据恢复、播放器或相机更新。
- `inflate`、`measure`、`layout`、`draw-VRI[...]`：View 系统工作。
- FrameTimeline：用户可见帧结果。

### 4. 修复匹配根因

- 生命周期初始化重复：移到 ViewModel、数据层或可复用缓存，并保证新 Activity 能恢复状态。
- `Bundle` 过大：只保存恢复所需的小型键值，数据从持久层重建。
- 热更新过重：把数据工作移出配置回调，UI 按帧合并到最新状态。
- 限定符资源未刷新：恢复默认重建，或补齐手工更新逻辑。
- 连续窗口变化：取消使用旧尺寸的任务，避免丢弃合法的 `Configuration`。
- 资源内存增长：用堆引用路径和原生内存分配找出持有者，再调整生命周期。

## 版本演进

| 版本 | 相关变化 |
|---|---|
| Android 12 / API 31–32 | 大屏、折叠屏与多窗口让 Configuration 变化更频繁；FixedRotation 与窗口过渡路径持续演进 |
| Android 13 / API 33 | 平台提供单应用语言 API，应用级语言成为常见配置来源 |
| Android 14–15 | 显示兼容、窗口模式与资源更新策略继续演进，具体行为应按对应源码标签核对 |
| Android 16 / API 36 | 大屏开始忽略方向、宽高比和 resize 限制，仍提供临时退出选项 |
| Android 17 / API 37 | 目标 SDK 37 的大屏退出选项移除；五类低频配置默认减少 Activity 重建；新增 `recreateOnConfigChanges` 适配路径；未自行处理的配置重建不再恢复旧 IME 可见状态 |

## 源码阅读入口

- `ResourcesKey.java`：资源缓存键的准确字段。
- `Resources.java`、`ResourcesImpl.java`：资源历史、AssetManager 与实现层状态。
- `ResourcesManager.java`：弱引用缓存、全局配置更新、Activity 覆盖配置与 `ResourcesImpl` 重定向。
- `ConfigurationController.java`：应用进程级配置更新和组件回调。
- `ActivityTaskManagerService.java`、`WindowProcessController.java`：`system_server` 的全局配置更新与进程派发。
- `ActivityRecord.java`：合并后配置、`shouldRelaunchLocked()` 与 Activity 级派发。
- `AppCompatRecreateOnConfigChangePolicy.java`：Android 17 减少重建的资源限定符判断。
- `ActivityRelaunchItem.java`、`ActivityThread.java`：`activityRestart` 与应用进程内的重建生命周期。
- `DisplayContent.java`、`WindowToken.java`：FixedRotation 的模拟旋转配置与窗口变换。
- `attrs_manifest.xml`：`configChanges` 与 `recreateOnConfigChanges` 的平台语义。
- `ActivityManagerService.java`：内部资源转储的服务端入口与边界。

## 参考资料

- [Android Developers：处理 Configuration 变化](https://developer.android.com/guide/topics/resources/runtime-changes)
- [Android Developers：`<activity>` Manifest 属性](https://developer.android.com/guide/topics/manifest/activity-element#config)
- [Android 17：面向 API 37 的行为变化](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android 17：影响所有应用的行为变化](https://developer.android.com/about/versions/17/behavior-changes-all)
- [Android 17：大屏忽略方向与 resizability 限制](https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored)
- [Android Developers：Compose 状态保存](https://developer.android.com/develop/ui/compose/state-saving)
- [ResourcesManager.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ResourcesManager.java)
- [ResourcesKey.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/res/ResourcesKey.java)
- [Resources.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/res/Resources.java)
- [ResourcesImpl.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/res/ResourcesImpl.java)
- [ConfigurationController.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ConfigurationController.java)
- [ActivityThread.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [ActivityRelaunchItem.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/servertransaction/ActivityRelaunchItem.java)
- [ActivityConfigurationChangeItem.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/servertransaction/ActivityConfigurationChangeItem.java)
- [ActivityRecord.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/ActivityRecord.java)
- [AppCompatRecreateOnConfigChangePolicy.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/AppCompatRecreateOnConfigChangePolicy.java)
- [DisplayContent.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/DisplayContent.java)
- [WindowToken.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowToken.java)
- [attrs_manifest.xml @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml)
- [ActivityManagerService.java @ android-17.0.0_r1](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java)
