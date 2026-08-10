---
title: "ResourcesManager 与 Configuration 变更性能"
chapter: "1.24"
status: "finalized"
drafted_date: "2026-06-04"
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1 ResourcesManager / ResourcesKey / ConfigurationController / ActivityRecord / ActivityThread / AppCompatRecreateOnConfigChangePolicy / DisplayContent / WindowToken；Android 17 官方行为变更文档"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/guide/topics/resources/runtime-changes"
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/activity-element#config"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-17"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all"
  - type: official
    path: "https://developer.android.com/about/versions/17/changes/ff-restrictions-ignored"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/state-saving"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ResourcesManager.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/res/ResourcesKey.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/res/Resources.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/res/ResourcesImpl.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ConfigurationController.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/servertransaction/ActivityRelaunchItem.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/servertransaction/ActivityConfigurationChangeItem.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityRecord.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/AppCompatRecreateOnConfigChangePolicy.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/DisplayContent.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/WindowToken.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/res/res/values/attrs_manifest.xml @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ActivityManagerService.java @ android-17.0.0_r1"
tags: [resources, configuration, activity-recreation, performance, resourcesmanager, configChanges, edge-to-edge]
related_chapters: ["1.8", "2.12", "8.2", "16.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-04"
gap_source: "研究素材+AOSP结构"
gap_score: 16
gap_score_detail: "素材丰富度 3 | 相关性 4 | 读者需求度 4 | 时效性 5"
pipeline_stage: "ready-to-publish"
task6_state: reviewed
task9_state: "reviewed"
task2b_result: fixed
task2b_state: fixed
last_task2b_lite_at: 2026-06-30
task9_result: "pass-tech-review"
last_task9_at: "2026-07-03T04:37:48+08:00"
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: 2026-06-30
last_task6_at: "2026-07-03T04:11:01+08:00"
last_task9_autofix_at: "2026-07-02"
last_task9_audit: "2026-07-02"
last_task9_audit_log: "logs/deep-review/2026-07-02-13-audit.md"
last_task9_review_log: "logs/deep-review/2026-07-03-04-deep-review.md"
task6_review_notes_round3: "2026-07-03 Task6 revisiting-review round3 (post-Task9 autofix): pass-light-edit. L1 scan: 0 banned words (页面对齐 is page alignment = false positive), 0 high-freq violations. Frontmatter sources have 7 entries missing path values (minor metadata gap, not blocking). L2: structure intact, outline 9/9 anchors covered, extensions covered. No new L3/L4 issues. task9_result=auto-fixed (not pass-tech-review), cannot auto-promote."
task6_review_notes_round2: "2026-07-02 Task6 revisiting-review round2 (post-Task9 autofix): pass-light-edit. L1 fix: banned word 链路 x4 in body + x1 in frontmatter -> 路径/调用路径. Task9 idle audit auto-fixed enableLessActivityRecreationOnConfigChange scope, recreateOnConfigChanges compat change boundary, FixedRotation trace判定边界. L2: structure intact, outline 9/9 anchors covered. No new L3/L4 issues. task9_result=auto-fixed (not pass-tech-review), cannot auto-promote."
task9_review_notes: "2026-07-03 04:37 Task9 deep-review：ResourcesManager / ATMS / ActivityRecord / FixedRotation / AppCompatRecreateOnConfigChangePolicy Android 17 源码路径复核通过；无 P0/P1；1 条性能倍率数据待补实测，写入 suggestions；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-30 Task9 复审通过: Android 17 ResourcesManager/Configuration/FixedRotation/Compose 状态边界已按源码和官方行为限定复核，无新增 P0/P1。 | 2026-07-02 Task9 闲时抽检 AUTO-FIX: 修正 Android 17 enableLessActivityRecreationOnConfigChange 适用范围、recreateOnConfigChanges/compat change 边界、FixedRotation 与 Perfetto trace 判定边界；回到 Task6 复审。"
task9_p0_issues: 0
task9_p1_issues: 0
task9_p2_issues: 1
task2b_rework_issues: "2026-06-30 Task2B main: L3 content depth — added Perfetto-based Activity recreate measurement methodology with SQL; expanded foldable/multi-window section with Perfetto diagnostic queries, Samsung/Pixel Fold divergence patterns, and multi-window resize debouncing strategies"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-07-04
task9_reviewed_date: "2026-07-03"
task9_reviewed_by: "openclaw-task9"
finalized_by: "openclaw-task9-auto-promote"
finalized_date: "2026-07-03"
last_task6_audit: "2026-07-13"
last_task6_audit_notes: "Idle audit: Fixed L1 issues (对齐→页面对齐, reduced 通过/如果 usage), 12 sources still missing paths, applicable_versions includes Android 12 for comparison only"
---
# 1.24 ResourcesManager 与 Configuration 变更性能

一次旋转、折叠展开、窗口缩放或语言切换，应用可能只收到 `onConfigurationChanged()`，也可能销毁并重建 Activity。两条路径都会更新资源，性能成本却完全不同。

排查这类问题时，应依次确认发生变化的 Configuration 位、`system_server` 选择热派发还是 relaunch，再检查资源更新、状态恢复和首帧。Android 17 还改变了部分配置项的默认重建策略，旧版本经验不能直接套用。

当前源码锚点为 Android 17 / API 37 / AOSP `android-17.0.0_r1`，同时说明 Android 12–16 的演进边界。

## 一次 Configuration 变更经过哪些模块

系统级 Configuration 更新和单个 Activity 的 override Configuration 最终会在 `ActivityRecord.ensureActivityConfiguration()` 汇合。主路径如下：

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

这张图有两个需要分开的分支：

- **进程级配置**：`ConfigurationChangeItem` 更新应用进程的全局资源和组件回调。
- **Activity 级配置**：`ActivityRecord` 根据变化位、Manifest 和兼容策略决定 relaunch，或者把新的 merged override Configuration 热派发给现有 Activity。

多窗口 Activity 收到的不是一份孤立的全局配置。服务端把全局 Configuration 与 Activity 的 override Configuration 合并后再下发，窗口大小、displayId、rotation 和 app bounds 都可能来自 Activity 所在的容器。relaunch 路径还会在创建新 Activity 实例前应用待处理的进程配置，避免新实例读取旧 Resources。

## Resources、ResourcesImpl 与 AssetManager

应用看到的资源对象分三层：

```text
Resources
  └─ ResourcesImpl
       └─ AssetManager
            └─ ApkAssets：base APK、split、overlay、shared library
```

- `Resources` 是公开 API 的包装层，也保存 ClassLoader 等调用上下文。
- `ResourcesImpl` 保存当前 `Configuration`、`DisplayMetrics`、资源缓存和 `AssetManager`。
- `AssetManager` 管理 base APK、split APK、overlay 和共享库的资源表与 native 对象。

多个 `Resources` 可以指向同一个 `ResourcesImpl`。因此，看到多个 Context 或 Resources 对象，不能据此认定原生资源表被完整复制了多份。

### ResourcesKey 保存什么

Android 17 的 `ResourcesKey` 包含：

| 字段 | 用途 |
|---|---|
| `mResDir`、`mSplitResDirs` | base APK 与 split 资源路径 |
| `mOverlayPaths`、`mLibDirs` | RRO overlay 与共享库资源路径 |
| `mDisplayId` | 覆盖默认 display 的资源目标 |
| `mOverrideConfiguration` | 叠加到全局配置之上的 override Configuration |
| `mCompatInfo` | 屏幕与密度兼容参数 |
| `mLoaders` | 动态 `ResourcesLoader` 集合 |

全局 `orientation`、`locale`、`screenWidthDp` 不会每次都直接复制进 key。`mOverrideConfiguration` 只保存相对全局配置的覆盖值。这个区别决定了缓存行为：全局 Configuration 改变时，系统通常更新现有 `ResourcesImpl`；不同 display、Activity override、资源路径或 loader 组合才需要不同 key。

### 全局配置更新会遍历现有 ResourcesImpl

`ResourcesManager.applyConfigurationToResources()` 的 Android 17 行为：

1. 用 `mResConfiguration.isOtherSeqNewer(config)` 检查配置序号；没有更新且 compat 不变时直接返回。
2. `mResConfiguration.updateFrom(config)` 更新进程级基准配置。
3. 遍历 `mResourceImpls`，把全局配置与每个 key 的 override 合并。
4. 调用 `ResourcesImpl.updateConfiguration()` 更新资源选择、metrics 和内部缓存。
5. Activity override、资源路径或 display 发生变化并需要不同实现时，通过 `redirectResourcesToNewImplLocked()` 让现有 `Resources` 改指向新的 `ResourcesImpl`。

源码提供的稳定 trace 名称是：

```text
ResourcesManager#applyConfigurationToResources
```

旋转一次就创建一个新 `ResourcesImpl`、拖动窗口时为每个尺寸都保留一份缓存，这两种推断都不成立。是否新建取决于 key 和 override 是否改变、旧 impl 是否还能复用。

## Activity 为什么会 relaunch

`ActivityRecord.shouldRelaunchLocked()` 的最终判断可以写成一个位运算：

```text
(changes & ~skipRelaunchConfigMask) != 0
```

`changes` 是新旧 merged Configuration 的差异位。`skipRelaunchConfigMask` 代表 Activity 或系统策略能够热处理的变化，Android 17 按以下来源逐步构造：

1. `ActivityInfo.getRealConfigChanged()`：Manifest 的 `android:configChanges`，加上旧 target SDK 的兼容位。
2. `CONFIG_RESOURCES_UNUSED`：Activity 声明不使用资源时跳过重建。
3. 旧 VR 应用的 `uiMode` 兼容规则。
4. desk mode 切换且应用没有 desk 资源时的跳过规则。
5. PiP 中的 density 变化。
6. display compatibility policy，例如尺寸兼容模式。
7. resource overlay policy 对 `CONFIG_ASSETS_PATHS` 的处理。
8. `AppCompatRecreateOnConfigChangePolicy.getRecreateConfigMask()`：包内存在相应限定符资源，或应用显式要求重建时，把这些位从 skip mask 中移除。

只要还有一个变化位未被 skip mask 覆盖，Activity 就会 relaunch。`orientation` 经常和 `screenSize`、`screenLayout`、窗口 bounds 一起变化，所以只声明 `orientation` 仍可能重建。

### 客户端重建顺序

`ActivityRelaunchItem.execute()` 在应用进程里建立名为 `activityRestart` 的 trace slice，然后调用 `ActivityThread.handleRelaunchActivity()`。后者先应用待处理的进程级 Configuration，再进入 `handleRelaunchActivityInner()`：

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

重建成本来自应用生命周期代码、状态保存、布局或 Composition 重建、资源冷缓存和新窗口首帧。它不等同于一次冷启动：进程通常还活着，Application、进程级单例、代码页和许多缓存仍可复用；但初始化很重的 Activity 也可能比普通热启动更慢。

## Android 17 减少了哪些 Activity 重建

Android 17 默认不再因为以下变化重建 Activity：

- `CONFIG_KEYBOARD`
- `CONFIG_KEYBOARD_HIDDEN`
- `CONFIG_NAVIGATION`
- `CONFIG_TOUCHSCREEN`
- `CONFIG_COLOR_MODE`
- `CONFIG_UI_MODE` 从 desk mode 切入或切出，且应用没有对应 desk 资源时

前五项由 `SKIP_ACTIVITY_RECREATION_ON_CONFIG_CHANGE` 与 `AppCompatRecreateOnConfigChangePolicy` 处理。策略还会扫描包内 `Configuration` 资源限定符；包内存在相应资源时，系统仍可把该变化放回 recreate mask。

依赖旧重建行为刷新界面的 Activity，可以在 Manifest 中显式声明 `android:recreateOnConfigChanges`：

```xml
<activity
    android:name=".InputActivity"
    android:recreateOnConfigChanges="keyboard|keyboardHidden|navigation|touchscreen|colorMode" />
```

同一配置位同时出现在 `configChanges` 和 `recreateOnConfigChanges` 时，以“不重建、由 Activity 处理”为结果。代码审查时应避免这种自相矛盾的声明。

这项 Android 17 变化不包含 `locale`、`layoutDirection`、`screenSize`、`smallestScreenSize`、`density`、普通 night mode 或 font scale。它们仍按 Manifest、资源限定符和 `shouldRelaunchLocked()` 的其他策略决定。

## configChanges 应该怎样用

`android:configChanges` 把资源和 UI 更新责任交给 Activity。系统仍会更新 Configuration，也仍会调用 `onConfigurationChanged()`；省掉的是 Activity 销毁与重建。

一个只准备自行处理旋转和窗口尺寸的 Activity，可以使用窄声明：

```xml
<activity
    android:name=".PlayerActivity"
    android:configChanges="orientation|screenSize" />
```

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

回调执行时，Activity 的 Resources 已切到新配置。应用需要更新所有受影响对象，包括自定义 View、播放器/相机变换、窗口 inset、缓存的尺寸、语言文本和嵌入组件。只调用 `super` 不能完成这些工作。

不建议为了性能把 `orientation|screenSize|screenLayout|smallestScreenSize|uiMode|locale|layoutDirection|density` 全部塞进 Manifest。每多接管一项，就多一类资源、第三方组件和状态需要人工刷新。默认 recreate 能自动重新选择 `layout-land`、`values-night`、`values-sw600dp`、本地化字符串和 density 资源，正确性成本通常更低。

选择标准很直接：

- 页面依赖大量限定符资源，或包含难以热更新的 View/Fragment：保留 recreate，优化状态恢复和初始化。
- 播放、相机、游戏或连续窗口动画不能中断，而且团队能维护完整更新逻辑：声明必要的 `configChanges`。
- 只为躲避某个卡顿而接管所有变化：先修 Activity 初始化和状态模型。

## FixedRotation 处理窗口过渡

FixedRotation 给 `WindowToken` 建立一个模拟旋转后的 `DisplayInfo`、`DisplayFrames` 和 Configuration，让窗口在 display 完成物理旋转前按目标方向布局和绘制。Android 17 中常见入口包括：

```text
DisplayContent.handleTopActivityLaunchingInDifferentOrientation()
  → setFixedRotationLaunchingApp()
     → startFixedRotationTransform()
        → WindowToken.applyFixedRotationTransform()
           → WindowToken.onFixedRotationStatePrepared()
```

系统也能对非顶部但可见、方向不同的 Activity 调用 `applyFixedRotationForNonTopVisibleActivityIfNeeded()`。

FixedRotation 不是“禁止 Activity recreate”的开关。`ActivityRecord.applyFixedRotationTransform()` 仍会调用 `ensureActivityConfiguration()`，后续是否 relaunch 继续由配置差异和 `shouldRelaunchLocked()` 决定。它主要处理旋转期间的窗口配置与 Surface 变换，减少画面跳变。

默认 Perfetto 不一定有 `applyFixedRotationTransform` 这类 Java 方法 slice。trace 里没有 `activityRestart` 只能证明没有走 Activity relaunch，不能反推 FixedRotation 一定参与。判断 FixedRotation 需要结合 WindowManager 日志、窗口状态和对应源码分支。

## Perfetto：区分热更新和 relaunch

Android 17 源码中可以直接依赖的 slice 名称如下：

| slice | 位置 | 说明 |
|---|---|---|
| `configChanged` | `ConfigurationController` | 进程级 Configuration 更新 |
| `ResourcesManager#applyConfigurationToResources` | `ResourcesManager` | 更新进程内 ResourcesImpl |
| `activityConfigChanged` | `ActivityConfigurationChangeItem` | Activity 热派发 |
| `activityRestart` | `ActivityRelaunchItem` | Activity relaunch |
| `performCreate:<Activity>` 等 | `Activity` | 新实例的生命周期阶段 |
| `inflate` | `LayoutInflater` | XML View 树构建 |
| `measure`、`layout`、`draw-VRI[...]` | `ViewRootImpl` | View 首帧遍历 |
| `Choreographer#doFrame <vsyncId>` | `Choreographer` | 应用帧执行 |

常见排查方式会搜索 `handleRelaunchActivity` 或 `handleConfigurationChanged`。方法名存在，不代表源码建立了同名 slice。Android 17 判断 relaunch 应优先查 `activityRestart`，判断热派发则查 `activityConfigChanged` 和 `configChanged`。

下面的 SQL 用于列出配置变化附近的稳定 slice。`performCreate:` 和 `Choreographer#doFrame` 带动态后缀，所以使用 `GLOB`：

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

如果应用自己的 `onConfigurationChanged()`、状态恢复或页面初始化没有 slice，可给关键区段添加自定义 marker：

```kotlin
Trace.beginSection("Cfg:updatePlayerLayout")
try {
    updatePlayerLayoutForCurrentWindow()
} finally {
    Trace.endSection()
}
```

用 FrameTimeline 判断用户是否看到卡顿，避免只看某个函数的 CPU 时间：

```sql
SELECT
  ts / 1e9 AS ts_s,
  dur / 1e6 AS frame_ms,
  jank_type
FROM actual_frame_timeline_slice
WHERE ts BETWEEN <start_ns> AND <end_ns>
ORDER BY ts;
```

采集时至少记录设备、build fingerprint、刷新率、Activity、触发方式、是否 relaunch、变化位和样本次数。relaunch 与热更新的对比必须使用同一页面、同一窗口状态和相同数据集，并报告 P50/P95，不能引用缺少测试条件的“快 5–10 倍”。

### 性能归因顺序

1. 有 `activityRestart`：查看 `performStop`、`performDestroy`、`performCreate`、`inflate` 和新窗口首帧。
2. 只有 `activityConfigChanged`：查看应用回调、自定义 marker、`measure/layout/draw`。
3. `ResourcesManager#applyConfigurationToResources` 很长：检查资源路径、overlay、多个存活的 ResourcesImpl 和资源缓存失效。
4. slice 都短但 FrameTimeline 仍 jank：检查主线程调度延迟、RenderThread、GPU 和 Surface/Window transition。
5. Configuration 短时间连续变化：按每次事件的 config 与窗口 bounds 分组，确认应用是否重复执行网络、解码、数据库或大对象构建。

## 多窗口与折叠屏的连续变化

折叠、展开、跨 display 和拖动自由窗口时，一次用户操作可能产生多次 merged Configuration。AOSP 不规定不同厂商必须以相同顺序更新 size、density、rotation 与窗口 posture，应用应把每次回调当作当前有效状态。

处理原则：

- 尺寸和布局更新要轻量，使用当前 window metrics 或新 Configuration 重新计算。
- 网络请求、图片解码、数据聚合等昂贵工作与尺寸回调解耦；同一任务可取消或复用。
- 需要按帧合并重复 UI 工作时，可以用 `postOnAnimation`、Compose 状态去重或可取消协程，但执行时重新读取最新窗口状态。
- 不要用“宽度变化小于 50dp 就丢弃”这类固定阈值。小变化也可能跨过资源断点、改变文字换行、窗口 inset 或相机裁剪。
- 不要等待一个不存在的“resize 手势结束”平台回调后才更新界面；拖动过程中用户也需要看到正确布局。

Jetpack WindowManager 的 `WindowInfoTracker` 用于观察折叠特征和窗口布局信息；Configuration 仍负责资源限定符与 Activity relaunch。两个信号描述的对象不同，不能互相替代。

## Android 17 的大屏方向与可调整大小策略

Android 16 已开始在大屏上忽略部分方向、宽高比和 resizable 限制，并提供临时退出选项。应用 target SDK 升到 Android 17 / API 37 后，这个退出选项不再可用。

在官方定义的大屏边界上，以下 Manifest 属性和运行时 API 可能被忽略：

- `screenOrientation`
- `resizeableActivity`
- `minAspectRatio`、`maxAspectRatio`
- `setRequestedOrientation()`、`getRequestedOrientation()` 对固定横竖屏值的请求

Android 17 文档列出的例外包括：`android:appCategory` 标记的游戏、用户在设备宽高比设置中显式选择应用默认行为，以及小于 sw600dp 边界的屏幕。

固定竖屏或 `resizeableActivity="false"` 已不能用来避免 Configuration 变化。target 37 的大屏测试至少覆盖：

- 横屏、竖屏和旋转中的状态保存；
- 分屏与桌面自由窗口连续 resize；
- 折叠态与展开态；
- 相机预览、视频画面和自定义 Surface 的宽高比与旋转；
- 窗口从一个 display 移到 density/rotation 不同的另一个 display。

可以在测试设备上启用 `UNIVERSAL_RESIZABLE_BY_DEFAULT` compat flag，提前观察限制被忽略后的行为。测试结果仍要以目标版本、设备窗口模式和官方例外为准。

## Android 17 的 IME 可见性变化

Android 17 中，应用没有自行处理 Configuration 变化、因而发生 Activity 重建时，系统不再恢复变化前的 IME 可见状态。页面若要求重建后继续显示键盘，需要明确请求：

- 对适合始终显示键盘的页面设置 `android:windowSoftInputMode="stateAlwaysVisible"`。
- 在新 Activity 的 `onCreate()` 完成输入框创建和焦点恢复后请求显示 IME。
- Activity 自行处理配置变化时，在 `onConfigurationChanged()` 中按业务状态决定是否保持或请求 IME。

不要无条件调用 `showSoftInput()`。输入框尚未 attach、没有 window focus 或焦点已转移时，请求可能无效，也可能把键盘错误地弹到不再需要输入的页面。

## Compose 与 View 的状态边界

### Compose

读取 `LocalConfiguration.current` 的 Composable 会在配置变化时重新组合。行为取决于 Activity 是否 relaunch：

| 边界 | `remember` | `rememberSaveable` | `ViewModel` | `SavedStateHandle` |
|---|---|---|---|---|
| 同一 Composition 内重组 | 保留 | 保留 | 保留 | 保留 |
| Activity relaunch | 丢失 | 从 Bundle 恢复 | 同一进程内保留原实例 | 可恢复小型 UI 状态 |
| 系统回收进程后重建 | 丢失 | 可从已保存实例状态恢复 | 原实例丢失 | 新 ViewModel 可恢复小型 UI 状态 |

`rememberSaveable` 和 `SavedStateHandle` 都使用 Bundle 边界。保存 ID、筛选项、输入文本和滚动位置；大型列表、Bitmap 或完整页面模型应保存在数据层，并用稳定 ID 重建。

Activity 自行处理 Configuration 时，Compose UI 可以通过 `LocalConfiguration` 更新；嵌入的 `AndroidView` 和 Fragment 不会因为 Compose 重组自动重建。它们原本依赖 Activity recreate 刷新资源和内部状态，因此需要应用显式更新。

### View 与 Fragment

View 页面保留默认 recreate 时，ViewModel 负责同一进程内的页面数据，已保存实例状态机制保存小型 UI 状态。新 Activity 会重新加载限定符资源和 View 树。

自行处理 Configuration 时，检查清单至少包括：

- 使用新 Resources 刷新字符串、颜色、drawable 和主题相关值；
- 根据新窗口 bounds 更新布局参数；
- 更新 Fragment 或自定义 View 中缓存的 density、方向和尺寸；
- 重新计算相机、视频、OpenGL/Vulkan Surface 的变换；
- 重新读取 window insets，不复用旧 Rect；
- 取消以旧尺寸启动、尚未完成的异步工作。

## createConfigurationContext 的使用边界

`Context.createConfigurationContext(override)` 会创建带 override Configuration 的 Context，适合局部资源查询、预览或隔离的显示环境：

```kotlin
val override = Configuration(baseContext.resources.configuration).apply {
    setLocales(LocaleList.forLanguageTags("zh-CN"))
}
val localizedContext = baseContext.createConfigurationContext(override)
val title = localizedContext.getString(R.string.title)
```

应用级语言优先使用 `LocaleManager.setApplicationLocales()` 或 AndroidX `AppCompatDelegate.setApplicationLocales()`。手工创建 Context 不会替应用完成 Activity、Service、通知和 Compose 的整体语言切换。

大量缓存不同 override Context，会让 `ResourcesManager` 同时维护更多 key/impl 组合。临时 Context 用完即释放，不要为每次绑定 View 创建一份并长期存入单例。

## Resources 内存诊断

Android 17 的 `mResourceImpls` 是 `ResourcesKey → WeakReference<ResourcesImpl>`。`Resources` 列表和 Activity 关联资源同样以弱引用保存；Activity token 映射使用 `WeakHashMap`。缓存容器本身不会强行保活 `ResourcesImpl`。

`resourcesManagerCacheLeakCleanup()` flag 开启时，`ReferenceQueue` 负责及时移除失效的键；全局配置更新也会删除已经失效的 weak reference。flag 未开启时，失效弱引用的键可能暂留在 map 中，但对应 impl 已可被 GC。map 项存在与原生对象仍存活是两回事。

Android 17 内部有 `ActivityManagerService.dumpResources()` / `dumpAllResources()`，客户端最终调用 `Resources.dumpHistory()`。这组接口按底层 `ApkAssets` 去重后输出资源历史和 assets，但 `android-17.0.0_r1` 没有提供稳定、公开的 `dumpsys activity resources <process>` 子命令。厂商调试工具即使暴露了内部 dump，也不能把输出项数直接解释为 `ResourcesKey` 数量；它同样不提供“最近创建时间”。

通用工具先看进程内存，再对 debuggable 进程抓堆：

```bash
adb shell dumpsys meminfo <package-name>
adb shell am dumpheap <process-name> /data/local/tmp/app.hprof
```

`am dumpheap` 受 debuggable、权限和设备策略限制。native AssetManager 或资源表分配要用 Perfetto native heap profiler；Java HPROF 看不到全部 native 成本。

资源相关内存持续增长时，按证据逐层确认：

1. 多次执行相同的旋转、语言切换或窗口 resize，观察进程 PSS/native heap 是否在 GC 后持续增长。
2. 用 Java heap dump 查看仍存活的 `Resources`、Context、Activity 与 `ResourcesImpl`，沿 GC Root 找强引用。
3. 用 native heap profiler 检查 AssetManager/资源相关分配，不能按 Java 对象数量估算每个 ResourcesImpl 的内存。
4. 在可调用内部 resource dump 的工程环境中对照 ApkAssets 路径，确认是否反复加载不同 split、overlay、shared library 或动态 ResourcesLoader；量产环境没有该入口时，从 heap 与加载日志取证。
5. 若只有失效弱引用的 key 数量增加、堆内存没有增长，不应定性为资源泄漏。

静态持有旧 Activity Context、长期保存局部 override Context、没有释放的主题/插件资源，都会让旧资源对象继续存活。单独看到多个 `ResourcesImpl` 仍不足以下结论；多 display、多 window 和不同 override 本来就可能需要多个实现。

## 一套可执行的排查流程

### 1. 确认变化位和 Activity 结果

- 记录新旧 Configuration 的 locale、uiMode、density、orientation、screenWidthDp、screenHeightDp、smallestScreenWidthDp 和 window bounds。
- 在 `onCreate()`、`onDestroy()`、`onConfigurationChanged()` 加带 Activity 实例标识的日志。
- 检查 Manifest 的 `configChanges`、`recreateOnConfigChanges`、方向和 resize 设置。

### 2. 用 trace 选择分支

- `activityRestart` 存在：分析 relaunch 生命周期与新窗口首帧。
- `activityConfigChanged` 存在且没有 `activityRestart`：分析热更新回调和 View/Compose 重排。
- 两者都没有：检查 trace 是否覆盖目标进程、atrace category 和正确的时间窗口。

### 3. 把系统成本与应用成本分开

- `ResourcesManager#applyConfigurationToResources`：framework 资源更新。
- 应用 marker：业务回调、数据恢复、播放器/相机更新。
- `inflate`、`measure`、`layout`、`draw-VRI[...]`：View 系统工作。
- FrameTimeline：用户可见帧结果。

### 4. 修复匹配根因

- 生命周期初始化重复：移到 ViewModel、repository 或可复用缓存，并保证新 Activity 能接回状态。
- Bundle 过大：只保存恢复所需的小型 key，数据从持久层重建。
- 热更新过重：把数据工作移出配置回调，UI 按帧合并到最新状态。
- 限定符资源未刷新：恢复默认 recreate，或补齐手工更新逻辑。
- 连续窗口变化：取消旧尺寸任务，避免丢弃合法 Configuration。
- 资源内存增长：用 heap root 和 native 分配证明持有者，再调整生命周期。

## 版本演进

| 版本 | 相关变化 |
|---|---|
| Android 12 / API 31–32 | 大屏、折叠屏与多窗口让 Configuration 变化更频繁；FixedRotation 与窗口过渡路径持续演进 |
| Android 13 / API 33 | 平台提供 per-app language API，应用级 locale 成为常见配置来源 |
| Android 14–15 | display compatibility、窗口模式与资源更新策略继续演进，具体行为应按对应 tag 核对 |
| Android 16 / API 36 | 大屏开始忽略方向、宽高比和 resize 限制，仍提供临时退出选项 |
| Android 17 / API 37 | target 37 37 的大屏退出选项移除；五类低频配置默认减少 Activity recreate；新增 `recreateOnConfigChanges` 适配路径；未自行处理的配置重建不再恢复旧 IME 可见状态 |

## 源码阅读入口

- `ResourcesKey.java`：资源缓存 key 的准确字段。
- `Resources.java`、`ResourcesImpl.java`：资源历史、AssetManager 与实现层状态。
- `ResourcesManager.java`：weak-reference 缓存、全局配置更新、Activity override 与 impl 重定向。
- `ConfigurationController.java`：应用进程级配置更新和组件回调。
- `ActivityTaskManagerService.java`、`WindowProcessController.java`：`system_server` 的全局配置更新与进程派发。
- `ActivityRecord.java`：merged Configuration、`shouldRelaunchLocked()` 与 Activity 级派发。
- `AppCompatRecreateOnConfigChangePolicy.java`：Android 17 减少重建的资源限定符判断。
- `ActivityRelaunchItem.java`、`ActivityThread.java`：`activityRestart` 与客户端 relaunch 生命周期。
- `DisplayContent.java`、`WindowToken.java`：FixedRotation 的模拟旋转配置与窗口变换。
- `attrs_manifest.xml`：`configChanges` 与 `recreateOnConfigChanges` 的平台语义。
- `ActivityManagerService.java`：内部 resource dump 的服务端入口与边界。

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
