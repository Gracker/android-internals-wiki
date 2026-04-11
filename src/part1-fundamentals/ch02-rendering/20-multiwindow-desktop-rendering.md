---
title: "多窗口与桌面模式渲染性能"
chapter: "2.20"
section: "2.20"
status: ready-for-review
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
last_verified: "2026-04-11"
last_verified_against: "AOSP android-16.0.0_r1 attrs_manifest.xml + Android Developers multi-window/desktop/connected displays/behavior changes 16 + Perfetto stdlib docs"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/guide/topics/large-screens/multi-window-support"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-16"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/layouts/adaptive/support-connected-displays"
  - type: official
    path: "https://perfetto.dev/docs/analysis/stdlib-docs"
  - type: official
    path: "https://source.android.com/docs/core/graphics/surfaceflinger"
  - type: aosp
    path: "frameworks/base/core/res/res/values/attrs_manifest.xml"
tags: [multiwindow, desktop-mode, split-screen, freeform, foldable, surfaceflinger, rendering]
related_chapters: ["2.6", "2.9", "2.12", "2.13", "7.4", "3.3"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task9_result: needs-rework
task2b_state: fixed
reviewed_date: "2026-04-11"
reviewed_by: "openclaw-task6"
task6_result: needs-rework
task2b_result: fixed
---

# 2.20 多窗口与桌面模式渲染性能

如果你在平板分屏、折叠屏展开态、PiP，或者外接显示器场景里看 trace，先变的往往不是 App 逻辑，而是同时可见的 window 和 layer 数量。SurfaceFlinger 要在同一个 display frame 里处理更多 layer state、更多 buffer acquire，以及更复杂的 composition decision。窗口一多，掉帧来源也会分叉，App 渲染慢是一类，SurfaceFlinger 合成慢是一类，HWC 资源不够又是一类。

读完本节，我们要能做三件事。第一，分清 split-screen、PiP、desktop windowing、connected displays 各自对应什么显示会话。第二，在 Perfetto 里把 App 侧和 SurfaceFlinger 侧的 jank 分开。第三，知道哪些优化属于 App 自己，哪些已经到了系统或设备实现边界。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **多窗口形态要按 display 会话拆开写**：[已验证: Android Developers multi-window support, support desktop windowing, support connected displays]
  分屏、PiP、freeform、desktop windowing、connected display 不共享一套边界。手机外接显示器时，手机和外屏可以是两套独立会话；desktop windowing 设备外接显示器时，桌面会话可以跨两块屏幕扩展。

- 🔹 **SurfaceFlinger 的压力来自 layer、composition 和 display 数量**：[已验证: source.android.com SurfaceFlinger 文档]
  多窗口先增加可见 layer，再提高 HWC 选择和 GPU composition 的概率。外接显示器还会把 display pipeline 再加一份。

- 🔹 **`recreateOnConfigChanges` 不是 Android 17 的通用窗口尺寸开关**：[已验证: AOSP `frameworks/base/core/res/res/values/attrs_manifest.xml`]
  当前公开 AOSP 里，这个属性针对的是 `mcc|mnc`。窗口尺寸、方向、screen layout 这些高频配置变化，仍然要看 `android:configChanges`、`onConfigurationChanged()` 和系统是否重建 Activity。

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

**Split-screen** 从 Android 7.0（API 24）开始进入平台主线。两个 App 同时可见，SurfaceFlinger 每一帧都要处理两组应用窗口，再加上分割线和系统栏。对渲染分析来说，重点不是“多了一个 App”，而是“多了一组持续变化的 layer 树”。

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

第三件事是 **display 可能不止一块**。connected display 场景里，SurfaceFlinger 不只是合成更多 layer，还可能同时维护手机内屏和外部显示器两套 display pipeline。外屏分辨率更高、刷新率不同，或者两边窗口树完全不同，都会让合成成本继续上升。

这里不要脱离设备条件写固定毫秒数。把某组固定毫秒数直接写成通用规律，离开 trace、设备型号、刷新率和显示分辨率，就没有复用价值。更稳妥的写法是直接回到观察面：看 layer 数量、看 compositionType、看 FrameTimeline，再决定是不是已经到了 SurfaceFlinger 侧瓶颈。

`dumpsys SurfaceFlinger` 适合做静态快照。它能帮我们核对当前有哪些可见 layer、哪些 layer 走 HWC、哪些 layer 走 GLES。Perfetto 适合看动态变化，尤其是窗口切换、拖拽缩放、PiP 持续播放、外接显示器插拔这些过程。

[待补充：同一设备在全屏、分屏、外接显示器三种形态下的 `dumpsys SurfaceFlinger` layer 对比截图]

## 配置变更和大屏适配，先把边界写对

### `recreateOnConfigChanges` 的公开语义

这部分先把一个常见误写删干净。当前公开 AOSP 里，`recreateOnConfigChanges` 不是 Android 17 新增的通用属性，也不是给屏幕尺寸、方向、density 这些变化准备的“快速通道”。`frameworks/base/core/res/res/values/attrs_manifest.xml` 里能核到的语义很窄，针对的是 `mcc|mnc` 这类运营商和区域配置变化。

窗口尺寸变化、方向变化、screen layout 变化这类多窗口场景里最常见的配置变化，还是要回到两条老路上看。要么系统按默认行为重建 Activity，要么 App 自己声明 `android:configChanges` 并在 `onConfigurationChanged()` 里接住变化。把这一层写错，后面关于“极短时间完成过渡”或者“官方轻量路径”的结论就会一起漂掉。

### Android 16 / 17 的真实边界

真正和大屏多窗口直接相关的边界，在 Android 16（API 36）和 Android 17（API 37）。

Android 12（API 31）把 multi-window 变成 large-screen 上的标准行为。公开文档写得很明确，大屏设备上平台会让所有 App 进入 multi-window 流程，不再按旧习惯把 `resizeableActivity="false"` 当成绝对开关；如果应用不能适配，系统会把它放进 compatibility mode。

Android 16（API 36）进一步把规则收紧到 `sw >= 600dp`。对 `targetSdkVersion >= 36` 的应用，平台会忽略 `screenOrientation`、`android:resizeableActivity="false"`、`minAspectRatio`、`maxAspectRatio`，以及 `setRequestedOrientation()` / `getRequestedOrientation()` 这类限制窗口形态的接口。文档同时给了临时 opt-out，写法是：

```xml
<activity ...>
    <property
        android:name="android.window.PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY"
        android:value="true" />
</activity>
```

这条 opt-out 只在 API 36 过渡期有效。行为变更文档已经写明，应用面向 API 37 之后，这个 opt-out 不再生效。到了 Android 17（API 37），`sw >= 600dp` 设备上的方向、宽高比和 resizability 限制会被平台直接忽略。

对应到渲染分析，结论也要跟着改。大屏和外接显示器上的窗口尺寸变化，会更频繁地触发 relayout、buffer 重新分配和 `performTraversals()`，但这不等于存在一个 Android 17 专用 manifest 属性帮你跳过整个过程。更稳妥的做法是保存 UI state，把窗口尺寸变化当成常态输入，而不是把它当成少见异常。

## Multi-resume 把“失去焦点”和“停止可见”拆开了

多窗口优化最容易写错的地方，就是把“失去焦点”近似成“进入 `onStop()`”。Android 10（API 29）之后，这个近似已经不成立。官方 multi-window 文档明确写了 multi-resume，多个可见 Activity 可以同时停留在 `RESUMED`。PiP 这类不具备焦点的窗口可能被 pause，但只要 Activity 还在屏幕上，生命周期就不能按“后台窗口已经停掉”去推导。

真正和独占资源绑定的是 **top resumed**。官方建议用 `onTopResumedActivityChanged()` 处理相机、麦克风这类一次只能被一个窗口稳定持有的资源。对渲染也一样。高频动画、连续 invalidation、激进的 frame rate vote，应该跟 top resumed 或真实可见性绑定，不该只盯 `onStop()`。

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
- `onStop()` 只在 Activity 真正离开屏幕时触发。彻底停止 offscreen work，放这里才对。

PiP 也要单独看。它经常是“可见，但不 focusable”。如果 PiP 还在持续播放视频，你不能把它当成静态后台窗口；如果 PiP 只是一个暂停状态的小窗，也没必要让它每帧都做完整 UI 刷新。

## Perfetto 和 dumpsys 的正确观察面

多窗口分析里，Perfetto 最怕两种写法。第一种是把不存在的表名写进 SQL。第二种是把某个版本里的 slice 名写成平台通用名称。

### 1. 先列出当前 trace 里的 SurfaceFlinger slice 名

`doCompose` 不能直接写成通用过滤条件。更稳妥的做法，是先在当前 trace 里列出 SurfaceFlinger 线程上真正存在的 slice 名，再挑和合成相关的项继续看：

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
  l.layer_name
FROM surfaceflinger_layers_snapshot s
JOIN surfaceflinger_layer l ON l.snapshot_id = s.id
ORDER BY s.ts DESC, l.layer_name
LIMIT 100;
```

这个查询适合先看“当前有多少 layer、名字是什么”。后面如果要继续和窗口拖拽、分屏切换、PiP 播放关联，再按时间区间收窄。

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
| 16 (API 36) | `sw >= 600dp` 时忽略方向、宽高比和 resizability 限制；提供临时 opt-out；connected displays 进入正式能力 | 窗口尺寸变化更频繁，外接显示器把 display 维度也拉进来 |
| 17 (API 37) | API 36 的 opt-out 对 target 37 不再生效 | `sw >= 600dp` 上的自适应布局从建议变成硬边界 |

## 常见问题与误区

### 误区 1：失去焦点就等于进入 `onStop()`

不对。Android 10 之后，多窗口里的多个可见 Activity 可以同时停留在 `RESUMED`。焦点、可见性、top resumed 是三套不同信号。把它们混成一个状态，优化策略很容易写偏。

### 误区 2：`recreateOnConfigChanges` 能处理折叠屏和窗口尺寸变化

就当前公开 AOSP 和开发者文档能核到的内容，这个属性的公开语义不在这里。折叠屏展开、窗口缩放、横竖屏切换这些场景，还是先查 `android:configChanges`、`onConfigurationChanged()`、状态保存，以及系统是否触发 Activity 重建。

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
  - <https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing>
  - <https://developer.android.com/develop/ui/compose/layouts/adaptive/support-connected-displays>
  - <https://perfetto.dev/docs/analysis/stdlib-docs>
  - <https://source.android.com/docs/core/graphics/surfaceflinger>
