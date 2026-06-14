---

title: 多窗口与桌面模式渲染性能
chapter: '2.20'
section: '2.20'
status: "finalized"
drafted_date: '2026-04-08'
drafted_by: openclaw-task2a
applicable_versions: Android 7.0 (API 24) - Android 17 (API 37)
last_verified: '2026-06-14'
last_verified_against: AOSP android-16.0.0_r1 attrs_manifest.xml + Android Developers
  multi-window/desktop/connected displays/behavior changes 16/17/release notes
  + Android Developers Blog first beta Android 17 + Perfetto stdlib/FrameTimeline docs
  + Source Android SurfaceFlinger/HWC docs
confidence: medium
sources:
- type: official
  path: https://developer.android.com/guide/topics/large-screens/multi-window-support
- type: official
  path: https://developer.android.com/about/versions/16/behavior-changes-16
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/about/versions/17/release-notes
- type: official
  path: https://developer.android.com/blog/posts/the-first-beta-of-android-17
- type: official
  path: https://developer.android.com/reference/android/R.attr#recreateOnConfigChanges
- type: official
  path: https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing
- type: official
  path: https://developer.android.com/develop/ui/compose/layouts/adaptive/support-connected-displays
- type: official
  path: https://perfetto.dev/docs/analysis/stdlib-docs
- type: official
  path: https://perfetto.dev/docs/data-sources/frametimeline
- type: official
  path: https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager
- type: official
  path: https://source.android.com/docs/core/graphics/hwc
- type: aosp
  path: frameworks/base/core/res/res/values/attrs_manifest.xml
tags:
- multiwindow
- desktop-mode
- split-screen
- freeform
- foldable
- surfaceflinger
- rendering
related_chapters:
- '2.6'
- '2.9'
- '2.12'
- '2.13'
- '7.4'
- '3.3'
pipeline_stage: "ready-to-publish"
task6_state: "reviewed"
task9_state: "reviewed"
task9_result: "pass-tech-review"
task2b_state: "fixed"
reviewed_date: "2026-06-14"
finalized_date: "2026-06-14"
finalized_by: "openclaw-task9-auto-promote"
auto_promoted_date: "2026-06-14"
auto_promoted_by: "openclaw-task9"
reviewed_by: openclaw-task6
task6_result: pass-light-edit
task2b_result: fixed-lite
task9_reviewed_date: "2026-06-14"
last_task9_at: "2026-06-14T20:37:52+08:00"
last_task2b_at: '2026-05-09T17:20:00+08:00'
task9_reviewed_by: "openclaw-task9"
last_task9_audit: "2026-06-14"
last_task9_audit_at: "2026-06-14T14:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-14-14-audit.md"
last_task2b_lite_at: "2026-05-31"
last_task6_at: "2026-06-14T16:05:00+08:00"
last_task6_review_log: "logs/review/2026-06-14-16-review.md"
task6_review_notes: "2026-06-14 Task6 16:05：Task9 auto-fixed 后写作复审。L1 禁用词/高频词/翻译腔扫描全干净。L2 修 1 处空标题（Android 16 桌面模式公开边界段落归位）。锚点 5/5 覆盖。无 L3/L4 回炉项。task9_result=auto-fixed 非 pass-tech-review，未自动晋升。"
last_task9_review_log: "logs/deep-review/2026-06-14-20-deep-review.md"
last_task9_autofix_at: "2026-06-14"
task9_review_notes: "2026-06-14 Task9 full review: pass-tech-review。复核 Android 16/17 大屏行为、recreateOnConfigChanges、multi-resume、connected display、Perfetto SurfaceFlinger schema 与 FrameTimeline jank 名称；未发现新增 P0/P1/P2，queue 无本章节 pending，自动晋升 finalized。"
p0: 0
p1: 0
p2: 0
last_task2b_verifier_at: "2026-06-14T19:31:17"
task2b_verifier_result: "task9-state-reset-ready-for-task9"
---

# 2.20 多窗口与桌面模式渲染性能

如果你在平板分屏、折叠屏展开态、PiP，或者外接显示器场景里看 trace，先变化的通常是同时可见的 window 和 layer 数量，而不是 App 逻辑本身。SurfaceFlinger 要在同一个 display frame 里处理更多 layer state、更多 buffer acquire，以及更复杂的 composition decision。窗口一多，掉帧来源也会分叉，App 渲染慢是一类，SurfaceFlinger 合成慢是一类，HWC 资源不够又是一类。

读完本节，我们要能做三件事。第一，分清 split-screen、PiP、desktop windowing、connected displays 各自对应什么显示会话。第二，在 Perfetto 里把 App 侧和 SurfaceFlinger 侧的 jank 分开。第三，知道哪些优化属于 App 自己，哪些已经到了系统或设备实现边界。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **多窗口形态要按 display 会话拆开写**：[已验证: Android Developers multi-window support, support desktop windowing, support connected displays]
  分屏、PiP、freeform、desktop windowing、connected display 不共享一套边界。手机外接显示器时，手机和外屏可以是两套独立会话；desktop windowing 设备外接显示器时，桌面会话可以跨两块屏幕扩展。

- 🔹 **SurfaceFlinger 的压力来自 layer、composition 和 display 数量**：[已验证: source.android.com SurfaceFlinger 文档]
  多窗口先增加可见 layer，再提高 HWC 选择和 GPU composition 的概率。外接显示器还会把 display pipeline 再加一份。

- 🔹 **`recreateOnConfigChanges` 是显式请求重建的补充开关**：[已验证: AOSP `frameworks/base/core/res/res/values/attrs_manifest.xml`, Android Developers `android.R.attr#recreateOnConfigChanges`]
  这个属性用于声明哪些配置变化仍应触发 Activity 重建。Android O 口径主要覆盖 `mcc|mnc`，API 37 又覆盖 keyboard、navigation、touchscreen、colorMode、部分 uiMode 等默认不再重建的变化；它仍不能当成窗口尺寸和方向变化的通用处理方案。

- 🔹 **Android 10 之后，multi-resume 改写了优化边界**：[已验证: Android Developers multi-window support]
  多窗口下多个可见 Activity 可以同时停留在 `RESUMED`。失去焦点不等于进入 `onStop()`，独占资源和高频渲染要参考 `onTopResumedActivityChanged()`。

- 🔹 **Perfetto 里要用真实 schema 和真实 jank 名称**：[已验证: Perfetto stdlib docs, FrameTimeline docs]
  layer 表是 `surfaceflinger_layers_snapshot` 和 `surfaceflinger_layer`。FrameTimeline 里 SurfaceFlinger 侧的 jank 分类是 `SurfaceFlingerCpuDeadlineMissed` 和 `SurfaceFlingerGpuDeadlineMissed`，正文里要统一用这两个正式名称。

### 扩展（可选深入）

- 🔸 折叠屏和外接显示器都可能触发 relayout、buffer 重新分配和更频繁的 `performTraversals()`，可与 §2.12、§2.13 对照阅读。
- 🔸 多窗口渲染分析如果要继续深入，下一步通常是看 §7.4 典型场景分析，或者直接去 Perfetto SQL 做 layer / frame timeline 联合观察。
<!-- outline-end -->

## 多窗口形态和 display 会话

先把几个容易混在一起的名词拆开。

**Split-screen** 从 Android 7.0（API 24）开始进入平台主线。两个 App 同时可见，SurfaceFlinger 每一帧都要处理两组应用窗口，再加上分割线和系统栏。对渲染分析来说，重点是多了一组持续变化的 layer 树，而不只是多了一个 App。

**PiP** 从 Android 8.0（API 26）扩展到小屏设备。PiP 窗口面积不大，但它常常持续提交视频帧或地图帧。主窗口和 PiP 小窗都在刷新时，SurfaceFlinger 侧看到的是一组前景主窗口，再叠一组持续更新的小窗 layer。

**Freeform / desktop windowing** 不能和“手机连外接显示器”写成一回事。公开文档把这两条线分得很清楚。desktop windowing 讲的是兼容设备上的可调整大小窗口，用户可以同时打开多个可调整大小的 app window，底部有 taskbar，窗口顶部有标题栏和最小化、最大化控制。connected displays 讲的是设备接到外部显示器后，桌面会话怎么分布到两块屏幕上。

下表把这几个形态放到同一张表里看，边界会清楚很多。

| 场景 | 公开边界 | 会话形态 | 渲染观察点 |
|---|---|---|---|
| Split-screen | Android 7.0（API 24）平台支持 | 一块屏幕里并排两个可见 app window | 同时可见 layer 增多，分割线和系统栏常驻 |
| PiP | Android 8.0（API 26）扩展到小屏 | 一块屏幕里主窗口 + 持续更新的小窗 | 小窗经常持续提交 buffer，主窗口和小窗互相叠加 |
| Freeform / desktop windowing | 大屏 / 兼容设备上的可调整大小窗口 | 一块或多块屏幕里的多个可调整大小窗口 | layer 数量和窗口遮挡关系更复杂，composition decision 更频繁 |
| 手机 + connected display | 手机连接外接显示器 | 手机保持原有状态，外屏启动独立 desktop session，两边是两套系统 | SurfaceFlinger 同时驱动两个 display，会话彼此独立 |
| desktop windowing 设备 + 外接显示器 | 平板等 desktop windowing 设备连接外屏 | 桌面会话跨两块屏幕扩展，窗口和光标可跨屏移动 | 仍是同一套桌面会话，但 display 范围更大、像素更多 |

[图：split-screen、PiP、desktop windowing、connected display 四种形态的 display 会话示意图]

## SurfaceFlinger 在多窗口下多了什么工作

多窗口对 SurfaceFlinger 的影响，主要落在三件事上。

第一件事是 **可见 layer 更多**。一个普通全屏 App 只有一组主窗口 layer，再叠系统栏。分屏把第二个 App 的主窗口树加进来，PiP 再叠一层持续更新的小窗，freeform 和 desktop windowing 还会继续增加窗口标题栏、阴影、taskbar 等系统 layer。

第二件事是 **composition decision 更复杂**。HWC 的 overlay plane 数量受 SoC 和显示路径限制，layer 数量、尺寸、alpha、rotation、pixel format 任何一项不合适，部分 layer 就会走 GPU composition。窗口少的时候，这种回退未必明显。窗口一多，回退出现得更频繁，SurfaceFlinger 主线程和 GPU 两边的时间都容易被拉长。

第三件事是 **display 可能不止一块**。connected display 场景里，SurfaceFlinger 可能同时维护手机内屏和外部显示器两套 display pipeline。外屏分辨率更高、刷新率不同，或者两边窗口树完全不同，都会让合成成本继续上升。

多 display 还会把 VSync 和 deadline 观察拆成两份。60Hz 内屏加 120Hz 外屏时，不能拿一条固定帧预算解释全部掉帧；要按目标 display 看对应的 frame timeline、presentation deadline、SurfaceFlinger slice 和 layer 集合。某块屏幕出现 `SurfaceFlingerCpuDeadlineMissed`，只说明这块 display 的提交或合成没赶上 deadline，不能直接外推到另一块屏幕。

这里不要脱离设备条件写固定毫秒数。把某组固定毫秒数直接写成通用规律，离开 trace、设备型号、刷新率和显示分辨率，就没有复用价值。直接回到观察面：看 layer 数量、看 compositionType、看 FrameTimeline，再决定是不是已经到了 SurfaceFlinger 侧瓶颈。

`dumpsys SurfaceFlinger` 适合做静态快照。它能帮我们核对当前有哪些可见 layer、哪些 layer 走 HWC、哪些 layer 走 GLES。Perfetto 适合看动态变化，尤其是窗口切换、拖拽缩放、PiP 持续播放、外接显示器插拔这些过程。

### Android 17 MessageQueue 优化不要外推到多 display 合成

Android 17 的 DeliQueue 是 `android.os.MessageQueue` 的无锁实现，公开数据里的第三方应用掉帧率下降约 4%、System UI / Launcher 交互掉帧率下降约 7.7%，对应的是 MessageQueue 锁竞争优化。它不能写成 SurfaceFlinger 多 display Transaction、Binder 路径或 `mGlobalLock` 拆分带来的多屏隔离收益。

多窗口 / 多 display trace 里仍然按 display 分开看 FrameTimeline、SurfaceFlinger slice 和 layer snapshot。某个 display 出现 `SurfaceFlingerCpuDeadlineMissed` 时，只能说明这一块 display 的合成或提交没有赶上 deadline；是否影响另一块屏幕，要回到同一时间段的 display 维度数据判断。

### Android 16 桌面模式公开边界

Android 16 desktop windowing 的公开特性应按官方文档写成 customizable header insets 和 app instance management。当前公开资料不能支撑"SurfaceControl 属性持久化缓存"或 Perfetto 中存在通用 `applyCachedState` slice 的结论。

### 16KB 页在多窗口下的内存叠加效应

Android 15 起 AOSP 支持 16KB page size，Google Play 从 2025-11-01 要求 targeting Android 15+ 的新应用和更新支持 16KB page sizes；AOSP 文档不支持把它写成 Android 16 旗舰设备强制默认。多窗口下的内存影响可以讨论，但 PSS +9%、四窗口额外内存接近一个完整应用 PSS 这类固定数字，需要绑定设备、构建、页面大小、进程常驻集和测量方法后再写。

在 Perfetto 中观察时，用 `process_memory` 数据源看多窗口场景下系统的 `MemAvailable` 变化趋势。如果切换窗口后可用内存持续下降且不回收，说明多窗口驻留的内存压力已经超过了系统的后台回收能力。优化方向是减少后台窗口的纹理缓存和 GPU buffer 持有量，在 `onTopResumedActivityChanged(false)` 时主动释放非必要资源。

[待补充：同一设备在全屏、分屏、外接显示器三种形态下的 `dumpsys SurfaceFlinger` layer 对比截图]

## 配置变更和大屏适配，先把边界写对

### `recreateOnConfigChanges` 的公开语义

`recreateOnConfigChanges` 的方向和 `android:configChanges` 相反。`configChanges` 表示“这类变化由 App 自己处理，系统不要重建 Activity”；`recreateOnConfigChanges` 表示“即使系统默认不重建，这类变化仍要按完整 Activity 生命周期重走一遍”。

这个属性的公开语义不是“所有配置变化的通用重启开关”。Android O 之后，`mcc|mnc` 默认不再触发 Activity 重建，应用可以用 `recreateOnConfigChanges` 显式要求这两类变化重建。API 37 又把 keyboard、keyboardHidden、navigation、touchscreen、colorMode，以及切入 / 切出 desk 模式这类 `uiMode` 变化纳入默认不重建范围；依赖完整重建加载资源的应用，需要在 manifest 中显式声明。

窗口尺寸变化、方向变化、screen layout 变化这类多窗口场景里的高频变化，仍要回到 `android:configChanges`、`onConfigurationChanged()`、状态保存和系统实际生命周期回调。把 `recreateOnConfigChanges` 写成“折叠屏或桌面模式尺寸变化开关”，会把大屏适配的判断带偏。

### Android 16 / 17 的真实边界

和大屏多窗口直接相关的边界，在 Android 16（API 36）和 Android 17（API 37）。

Android 12（API 31）把 multi-window 变成 large-screen 上的标准行为。公开文档写得很明确，大屏设备上平台会让所有 App 进入 multi-window 流程，不再按旧习惯把 `resizeableActivity="false"` 当成绝对开关；如果应用不能适配，系统会把它放进 compatibility mode。

Android 16（API 36）进一步把大屏规则扩展到 `sw >= 600dp`。对 `targetSdkVersion >= 36` 的应用，平台会忽略 `screenOrientation`、`android:resizeableActivity="false"`、`minAspectRatio`、`maxAspectRatio`，以及 `setRequestedOrientation()` / `getRequestedOrientation()` 这类限制窗口形态的接口。文档同时给了临时 opt-out，写法是：

```xml
<activity ...>
    <property
        android:name="android.window.PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY"
        android:value="true" />
</activity>
```

这条 opt-out 只在 API 36 过渡期有效。行为变更文档已经写明，应用面向 API 37 之后，这个 opt-out 不再生效。到了 Android 17（API 37），`sw >= 600dp` 设备上的方向、宽高比和 resizability 限制会被平台直接忽略。

这会改变 `android:configChanges` 的风险边界。应用仍然可以声明某些配置变化自行处理，但大屏上窗口被拉伸、旋转、进入分屏或桌面窗口时，系统给出的形态约束已经变少，Activity 更容易收到连续的尺寸、方向、screen layout 变化。声明了 `configChanges` 的应用也要真的更新资源、布局和渲染目标；没有声明或声明不完整时，系统仍可能走 Activity 重建路径。

API 37 的 `recreateOnConfigChanges` 要和这条大屏规则分开读。它面向 keyboard、keyboardHidden、navigation、touchscreen、colorMode、部分 desk `uiMode` 变化，用来恢复“发生这些变化时重建 Activity”的旧行为；它不会让 `screenOrientation`、宽高比或 resizability 限制重新生效。对应到渲染分析，大屏和外接显示器上的窗口尺寸变化，会更频繁地触发 relayout、buffer 重新分配和 `performTraversals()`。保存 UI state，把窗口尺寸变化当成常态输入，不要把它当成少见异常。

## Multi-resume 把“失去焦点”和“停止可见”拆开了

多窗口优化最容易写错的地方，就是把“失去焦点”近似成“进入 `onStop()`”。Android 10（API 29）之后，这个近似已经不成立。官方 multi-window 文档明确写了 multi-resume，多个可见 Activity 可以同时停留在 `RESUMED`。PiP 这类不具备焦点的窗口可能被 pause，但只要 Activity 还在屏幕上，生命周期就不能按“后台窗口已经停掉”去推导。

和独占资源绑定的是 **top resumed**。官方建议用 `onTopResumedActivityChanged()` 处理相机、麦克风这类一次只能被一个窗口稳定持有的资源。对渲染也一样。高频动画、连续 invalidation、激进的 frame rate vote，应该跟 top resumed 或真实可见性绑定，不该只盯 `onStop()`。

```kotlin
override fun onTopResumedActivityChanged(topResumed: Boolean) {
    super.onTopResumedActivityChanged(topResumed)
    if (topResumed) {
        resumeHighFrequencyRendering()
        reacquireExclusiveResources()
    } else {
        dropNonEssentialAnimations()
        releaseExclusiveResources()
    }
}

override fun onStop() {
    super.onStop()
    stopOffscreenWork()
}
```

这段代码背后的分工要说清楚。

- `topResumed = true`，窗口拿到前台交互资格。相机、麦克风、手写、游戏主循环这类要争抢独占资源的工作，放在这里最稳。
- visible 但不是 top resumed，窗口可能还在 `RESUMED`。视频小窗、导航小窗、分屏副窗口都可能属于这一类。这里适合做“降频”和“减少无效重绘”，不适合一刀切停掉全部渲染。
- `onStop()` 只在 Activity 离开屏幕时触发。停止 offscreen work，放这里才对。

PiP 也要单独看。它经常是“可见，但不 focusable”。如果 PiP 还在持续播放视频，你不能把它当成静态后台窗口；如果 PiP 只是一个暂停状态的小窗，也没必要让它每帧都做完整 UI 刷新。

## Perfetto 和 dumpsys 的正确观察面

多窗口分析里，Perfetto 最怕两种写法。第一种是把不存在的表名写进 SQL。第二种是把某个版本里的 slice 名写成平台通用名称。

### 1. 先列出当前 trace 里的 SurfaceFlinger slice 名

`doCompose` 不能直接写成通用过滤条件。先在当前 trace 里列出 SurfaceFlinger 线程上存在的 slice 名，再挑和合成相关的项继续看：

```sql
SELECT DISTINCT slice.name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
WHERE thread.name = 'SurfaceFlinger'
ORDER BY 1;
```

这样做的好处很直接。版本升级、厂商裁剪、trace config 改动时，slice 名有没有变，一眼就知道。

### 2. layer 快照表要用真实 schema

公开 stdlib 文档里，SurfaceFlinger layer 快照对应的表是 `surfaceflinger_layers_snapshot` 和 `surfaceflinger_layer`。写成 `surfaceflinger_layers`，读者大概率直接跑不通。一个能直接跑的查询可以写成这样：

```sql
SELECT
  s.ts / 1e6 AS ts_ms,
  l.layer_name,
  l.is_visible,
  l.hwc_composition_type
FROM surfaceflinger_layers_snapshot s
JOIN surfaceflinger_layer l ON l.snapshot_id = s.id
WHERE l.is_visible = 1
ORDER BY s.ts DESC, l.layer_name
LIMIT 100;
```

这个查询适合先看“当前有哪些可见 layer、名字是什么、HWC composition type 是什么”。Perfetto stdlib 的 `surfaceflinger_layer` 表没有 `display_id` 列，connected display trace 里不能直接写 `WHERE l.display_id = 0`。需要区分 display 时，先在 Winscope SurfaceFlinger 视图，或 `android_surfaceflinger_display` / transaction 表里确认 display id 与 layer 归属，再按目标时间片收窄。

### 3. FrameTimeline 的 jank 名称要写全

FrameTimeline 里，App 侧和 SurfaceFlinger 侧至少要分成三类：

- `AppDeadlineMissed`，App 自己没有按时交帧。
- `SurfaceFlingerCpuDeadlineMissed`，SurfaceFlinger 主线程没有在 deadline 前完成 CPU 侧工作。
- `SurfaceFlingerGpuDeadlineMissed`，CPU 侧推进了，GPU composition 还是没赶上。

多窗口场景下，后两类更有价值。窗口多、layer 多、display 多，先把 SurfaceFlinger 侧 miss 和 App 侧 miss 拆开，再决定是不是回头看应用主线程、RenderThread、图片上传、视频解码，还是继续沿着 SurfaceFlinger / HWC / GPU composition 往下查。

[图：Perfetto 中 SurfaceFlinger 主线程 slice、FrameTimeline jank_type、layer snapshot 三者的对照图]

## 版本演进

| Android 版本 | 公开变化 | 对渲染分析的影响 |
|---|---|---|
| 7.0 (API 24) | 引入 split-screen，freeform capability 进入平台能力 | SurfaceFlinger 开始稳定面对多个可见 app window |
| 8.0 (API 26) | PiP 扩展到小屏设备 | 主窗口之外多了一条持续更新的小窗 layer |
| 10 (API 29) | multi-resume + `onTopResumedActivityChanged()` | 失去焦点不再等于离开 `RESUMED`，生命周期判断要更细 |
| 12 (API 31) | large-screen 上 multi-window 成为标准行为 | 平板、折叠屏更频繁进入 resizable / compatibility mode |
| 16 (API 36) | `sw >= 600dp` 时忽略方向、宽高比和 resizability 限制；提供临时 opt-out；connected displays 进入正式能力；desktop windowing 公开 customizable header insets 与 app instance management | 窗口尺寸变化更频繁，外接显示器把 display 维度也拉进来；桌面窗口标题栏和多实例管理会改变窗口交互与任务组织 |
| 17 (API 37) | API 36 的 opt-out 对 target 37 不再生效；`android.os.MessageQueue` 引入 DeliQueue lock-free 优化 | `sw >= 600dp` 上的自适应布局从建议变成硬边界；DeliQueue 的掉帧收益限于 MessageQueue 锁竞争口径，不能外推为 SurfaceFlinger 多 display 隔离 |

## 常见问题与误区

### 误区 1：失去焦点就等于进入 `onStop()`

不对。Android 10 之后，多窗口里的多个可见 Activity 可以同时停留在 `RESUMED`。焦点、可见性、top resumed 是三套不同信号。把它们混成一个状态，优化策略很容易写偏。

### 误区 2：`recreateOnConfigChanges` 能处理折叠屏和窗口尺寸变化

这个属性只声明“哪些默认不重建的配置变化仍要重建”。折叠屏展开、窗口缩放、横竖屏切换这些场景，还是查 `android:configChanges`、`onConfigurationChanged()`、状态保存，以及系统是否触发 Activity 重建。API 37 对 keyboard、navigation、touchscreen、colorMode、部分 desk `uiMode` 的处理，不应外推成窗口尺寸变化的通用方案。

### 误区 3：多窗口掉帧一定是 App 的问题

不对。多窗口把 SurfaceFlinger 一侧的变量放大了。先看 FrameTimeline 的 jank_type，再看 layer 快照和 compositionType。确认是 `SurfaceFlingerCpuDeadlineMissed` 或 `SurfaceFlingerGpuDeadlineMissed` 之后，再决定 App 还能做多少。

## 参考资料

- AOSP 源码路径：
  - `frameworks/base/core/res/res/values/attrs_manifest.xml`
  - `frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java`
  - `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`
- 官方文档：
  - <https://developer.android.com/guide/topics/large-screens/multi-window-support>
  - <https://developer.android.com/about/versions/16/behavior-changes-16>
  - <https://developer.android.com/about/versions/17/behavior-changes-17>
  - <https://developer.android.com/about/versions/17/release-notes>
  - <https://developer.android.com/blog/posts/the-first-beta-of-android-17>
  - <https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing>
  - <https://developer.android.com/develop/ui/compose/layouts/adaptive/support-connected-displays>
  - <https://perfetto.dev/docs/analysis/stdlib-docs>
  - <https://perfetto.dev/docs/data-sources/frametimeline>
  - <https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager>
  - <https://source.android.com/docs/core/graphics/hwc>
