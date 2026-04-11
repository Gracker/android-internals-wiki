---
title: "多窗口与桌面模式渲染性能"
chapter: "2.20"
status: ready-for-review
drafted_date: "2026-04-08"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
last_verified: "2026-04-08"
last_verified_against: "AOSP android-17-beta3"
confidence: medium
sources:
  - type: official
    path: "developer.android.com/guide/topics/large-screens"
  - type: official
    path: "source.android.com/docs/core/graphics/surfaceflinger"
  - type: blog
    path: "Android 16 Desktop Windowing — android.com"
tags: [multiwindow, desktop-mode, split-screen, freeform, foldable, surfaceflinger, rendering]
related_chapters: ["2.6", "2.9", "2.12", "2.13", "7.4", "3.3"]
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task9_result: needs-rework
task2b_state: pending
reviewed_date: "2026-04-11"
reviewed_by: "openclaw-task6"
task6_result: needs-rework
---

# 2.20 多窗口与桌面模式渲染性能

## 为什么要了解多窗口渲染

在 Android 7.0 引入分屏模式之前，系统同一时刻只有一个 App 的 Surface 是活跃的——SurfaceFlinger 的合成压力很低，HWC 叠加层的数量一般不会超过上限。但从 Android 7.0 到 Android 16，多窗口形态经历了从分屏、画中画、自由窗口到桌面模式的演进，这些形态都会增加同时可见的 Layer 数量。

这对渲染性能有直接影响：SurfaceFlinger 需要在每个 VSync 周期内完成更多 Layer 的合成，HWC 叠加层数量有限（通常 4-8 层），超出上限时回退到 GPU 合成会带来功耗和帧率的双重损失。折叠屏的折叠/展开、桌面模式外接显示器、Android 16 的大屏强制适配——这些场景都会触发多窗口渲染路径。

理解多窗口渲染机制，意味着我们能在 Perfetto 中快速定位"多窗口场景下掉帧"的根因：是 SurfaceFlinger 合成耗时过长，还是 App 本身渲染慢了，又或者是 HWC 回退到了 GPU 合成。

## Android 多窗口模式演进

Android 的多窗口支持经历了几个关键阶段，每个阶段都改变了 SurfaceFlinger 需要同时处理的 Layer 数量和复杂度。

**分屏模式（Split-Screen）**，Android 7.0（API 24）引入。屏幕被一分为二，两个 App 各占一半，中间一条分割线。两个 App 的 Surface 同时活跃，SurfaceFlinger 每帧需要合成的 Layer 从原来的"App + 系统 UI"变成了"App A + App B + 分割线 + 系统 UI"。表面上只是多了一个 App，但很多时候每个 App 都不止一个 Layer，比如 `SurfaceView` 会带来额外的 BufferQueue，Layer 数量可能从 3-4 层增长到 6-8 层。

**画中画模式（PiP）**，Android 8.0（API 26）引入。视频、导航类 App 进入小窗悬浮在主 App 上方。PiP 窗口的 Layer 通常尺寸较小但需要持续更新，主 App 的渲染不受 PiP 存在的影响——它们各自有独立的 Choreographer 和 VSync-app 回调。

**自由窗口模式（Freeform）**，Android 7.0 引入但默认只在 Chrome OS 上启用。多个 App 以可自由调整大小、可重叠的窗口形式存在。这是多窗口 Layer 并发量最大的形态，因为窗口数量不受限（分屏最多两个，PiP 只有一个小窗）。

**桌面窗口模式（Desktop Windowing）**，Android 16（API 36）QPR3 正式面向手机端推出。通过 USB-C 连接外部显示器，配合蓝牙键鼠，手机变成桌面设备。Pixel 8 及以上机型支持。这个模式下窗口数量、分辨率和刷新率都与手机屏幕不同，SurfaceFlinger 需要同时管理两套显示输出。

[图：Android 多窗口模式演进时间线——从分屏到桌面模式的 Layer 数量增长示意]

在 Perfetto 的 SurfaceFlinger 进程 Track 中，可以观察这些不同模式下的合成耗时差异。分屏模式下 SurfaceFlinger 每帧合成耗时一般在 2-4ms；自由窗口模式可能达到 6-10ms，接近一个 VSync 周期的预算。

## 多窗口下 SurfaceFlinger 的合成负载

SurfaceFlinger 的工作是在每个 VSync-sf 信号到来时，收集所有可见 Layer 的最新 Buffer，然后交给 HWC 或 GPU 合成为最终帧。多窗口对这个过程的影响体现在三个维度。

### Layer 数量增长

每个可见的 App 窗口至少贡献一个 Layer（通常是 SurfaceView 或 WindowSurface）。系统 UI（状态栏、导航栏、最近任务栏）也各自有独立的 Layer。在分屏模式下，Layer 数量通常为：

- 顶部状态栏：1 层
- App A 主窗口：1 层（可能还有 SurfaceView 的额外 Layer）
- 分割线：1 层
- App B 主窗口：1 层
- 底部导航栏：1 层

总计 5-7 层。如果是自由窗口模式打开 3 个 App，Layer 数量可能达到 8-12 层。

### HWC 叠加层数上限

Hardware Composer（HWC）的叠加层（Overlay Plane）数量由 SoC 厂商决定，主流平台通常支持 4-8 个叠加层。当 Layer 数量在叠加层上限内时，SurfaceFlinger 可以将所有 Layer 的 Buffer 直接送入显示控制器的叠加单元——不需要 GPU 参与合成，功耗最低。

但当 Layer 数量超过叠加层上限，或者某些 Layer 的属性不满足叠加要求（如复杂的像素格式、需要旋转、透明度混合系数超出硬件支持范围），SurfaceFlinger 会将这些"溢出"的 Layer 交给 GPU 合成一个中间 Buffer，再把中间 Buffer 作为一个 Layer 送入 HWC。

这个 GPU 合成回退（GLES Fallback）在多窗口场景中是性能问题的常见来源。我们可以通过 `adb shell dumpsys SurfaceFlinger` 查看每个 Layer 的合成方式：

```
# HWC 合成（高效，GPU 不参与）
Layer name:
  compositionType: HWC

# GLES 合成（回退，GPU 参与合成）
Layer name:
  compositionType: GLES
```

[待补充：分屏模式 vs 全屏模式下 dumpsys SurfaceFlinger 输出的 Layer 列表对比截图]

### 合成耗时与帧预算

SurfaceFlinger 在 VSync-sf 到来后开始合成工作，需要在下一个 VSync-sf 到来之前完成。以 60Hz 显示为例，VSync-sf 间隔 16.6ms，SurfaceFlinger 的合成预算也是 16.6ms。

在全屏模式下，SurfaceFlinger 合成耗时通常只有 1-3ms。但在多窗口模式下，随着 Layer 数量增加：
- 纯 HWC 合成：耗时增长有限（1-3ms → 2-5ms），因为硬件叠加是并行的
- 触发 GLES 回退：耗时可能飙到 8-15ms，因为 GPU 需要渲染合成 Buffer

在 Perfetto 中，SurfaceFlinger 进程下有 `nuRender` 类型的 Slice，表示每次合成的耗时。如果这个 Slice 的 dur 超过 8ms（60Hz 下半个 VSync 周期），就需要检查是不是触发了 GPU 合成回退。

## 折叠屏与多 Surface 渲染

折叠屏引入了一种特殊的多窗口场景：不是多个 App 同时可见，而是一个 App 在物理屏幕尺寸发生变化时需要重新适配。这涉及 Surface 的销毁和重建，如果处理不当会导致明显的卡顿。

### 折叠/展开时的 Surface 生命周期

当折叠屏折叠或展开时，屏幕尺寸和密度发生变化，系统发送 `Configuration.CHANGE_SCREEN_SIZE` 和 `Configuration.CHANGE_DENSITY` 等配置变更事件。默认行为是销毁当前 Activity 并重新创建。

这个销毁-重建过程对渲染管线的影响是：
1. 旧 Activity 的 Surface 被 SurfaceFlinger 移除
2. View 树被销毁，Choreographer 回调被注销
3. 新 Activity 的 Surface 在 SurfaceFlinger 中注册
4. 新的 View 树经历完整的 measure → layout → draw 流程
5. 第一帧渲染完成并提交到 SurfaceFlinger

从用户感知来看，这个过程可能导致 200-500ms 的黑屏或闪烁。在 Perfetto 中，我们可以在对应 App 进程的 Track 中看到一段没有 `Choreographer#doFrame` 的空白期，紧接着是一段较长的 `inflate` + `measure` + `layout`。

### Android 17 recreateOnConfigChanges

Android 17 引入了 `android:recreateOnConfigChanges` manifest 属性，允许 App 声明在特定配置变更时不重建 Activity。支持的配置变更包括 6 种：

```xml
<activity android:recreateOnConfigChanges="screenSize|smallestScreenSize|screenLayout|
    orientation|density|uiMode" />
```

当这些配置变更被声明后，系统只调用 `Activity.onConfigurationChanged()` 和 `View.onConfigurationChanged()`，不触发 Activity 销毁重建。对渲染管线的影响：
- Surface 不需要销毁和重建，SurfaceFlinger 中的 Layer 持续存在
- Choreographer 的 VSync 回调不中断
- View 树的 `requestLayout()` 在下一个 `doFrame` 中执行布局重算
- 整个过渡过程可以在 1-2 帧内完成（16-32ms），而非重建时的 200-500ms

[待验证：recreateOnConfigChanges 在 Android 17 beta 版本中的完整行为]

### BufferQueue 竞争

折叠屏在某些模式下（如展开态下的分屏），可能存在两个 App 同时竞争 GPU 资源的情况。每个 App 有独立的 BufferQueue（参见 §2.13），但 GPU 是共享的。如果两个 App 都在做复杂的渲染（如都有 RecyclerView 快速滑动），GPU 时间片分配可能导致其中一方掉帧。

在 Perfetto 中，我们可以在 GPU Track（如果设备支持 GPU profiling）看到 GPU 的利用率。如果多窗口下 GPU 利用率持续 > 90%，而某个 App 的 `Choreographer#doFrame` 耗时明显增长，这就是 GPU 竞争的信号。

## 桌面窗口模式的渲染架构变化

Android 16 的桌面窗口模式在渲染架构上引入了一个新维度：系统同时驱动两个显示输出——手机屏幕和外接显示器。

### 双显示输出的 SurfaceFlinger 调度

SurfaceFlinger 为每个物理显示设备维护独立的合成管线。在桌面模式下：

- **手机屏幕**：显示 Android 系统的常规界面（可能是一个简化的任务切换器或者保持当前 App）
- **外接显示器**：显示桌面环境，包含多个自由窗口、任务栏等

每个显示设备有独立的 VSync 信号和合成触发。SurfaceFlinger 内部为每个 `Display` 创建一个 `DisplayDevice` 对象，独立执行合成循环。对应到 CPU 开销，SurfaceFlinger 原来只处理一个 `Display` 的合成，现在要同时处理两个，负载会明显上升。

在 Perfetto 中，SurfaceFlinger 进程下的合成 Slice 会从一套变成两套，分别对应两个 `Display` 的合成周期。外接显示器的分辨率通常高于手机屏幕（如 1920×1080 或 2560×1440），高分辨率意味着 GPU 合成时需要处理更多像素，进一步增加合成耗时。

### 窗口独立的 VSync-app 与帧率控制

在桌面模式下，每个窗口的 App 有独立的 Choreographer 和 VSync-app 回调。这与分屏模式类似——分屏的两个 App 各自独立渲染。但桌面模式的窗口数量更多，如果所有窗口同时活跃渲染，SurfaceFlinger 需要处理的 BufferQueue 更新频率更高。

ARR（Adaptive Refresh Rate，参见 §2.18）在桌面模式下的行为取决于外接显示器是否支持可变刷新率。大多数桌面显示器支持 60Hz，部分高端型号支持 VRR（可变刷新率，如 48-144Hz）。如果外接显示器不支持 VRR，ARR 的帧率投票机制在外接显示器上无效，所有窗口锁定在显示器固有的刷新率。

## 多窗口性能分析与优化

### Perfetto 中多窗口场景的 Track 解读

分析多窗口性能时，Perfetto 中需要关注的 Track 和指标：

**1. SurfaceFlinger 进程**

- `nuRender` Slice：每次合成的耗时，多窗口下 dur 增长是正常的，但如果超过 10ms（60Hz 下）需要警惕
- Layer 数量：通过 SQL 查询 `surfaceflinger_layers` 表可以获取当前活跃 Layer 列表

**2. 各 App 进程**

- `Choreographer#doFrame`：每个 App 独立，关注各自的帧耗时
- `BufferQueue` Track：观察 Buffer 是否被及时消费（`acquireBuffer` 间隔），如果 Buffer 堆积说明 SurfaceFlinger 来不及合成

**3. FrameTimeline Track**

- `AppDeadlineMissed`：App 端渲染超时
- `SFDeadlineMissed`：SurfaceFlinger 合成超时
- 多窗口下更常见的是 SF 端的问题，因为合成负载更重

```sql
-- Perfetto SQL：查询多窗口场景下 SurfaceFlinger 合成耗时
SELECT
  slice.name,
  AVG(slice.dur) / 1e6 as avg_dur_ms,
  MAX(slice.dur) / 1e6 as max_dur_ms,
  COUNT(*) as frame_count
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
WHERE thread.name = 'SurfaceFlinger'
  AND slice.name LIKE '%doCompose%'
GROUP BY slice.name
```

### 常见性能问题

**焦点窗口掉帧**：桌面模式下，当前获得焦点的窗口应该获得优先的 GPU 时间片。但如果后台窗口（比如一个正在播放视频的小窗）持续提交帧，GPU 时间可能被分散。优化方式是在 `onWindowFocusChanged(false)` 时降低渲染频率。

**后台窗口无谓渲染**：分屏模式下，即使一个 App 不是焦点窗口，它仍然会收到 VSync-app 回调并执行 `doFrame`。如果这个 App 的 UI 不需要持续更新（比如一个静态列表），它每次 `doFrame` 中的 `draw` 步骤其实是不必要的。从 Android 12 开始，系统对非焦点 App 的 VSync 分发频率做了限制（从每帧降为每 2-3 帧一次），但这不适用于所有场景。

### 优化策略

**生命周期感知渲染**：在 `onStop()` 中停止所有动画和持续渲染逻辑，在 `onStart()` 中恢复。这不仅节省 CPU/GPU 资源，也减少 SurfaceFlinger 的合成压力。

```java
@Override
protected void onStop() {
    super.onStop();
    // 停止 RecyclerView 的 prefetch 和缓存清理
    recyclerView.getRecycledViewPool().clear();
    // 停止自定义动画
    animator.cancel();
}

@Override
protected void onStart() {
    super.onStart();
    // 恢复必要的渲染
    if (needsAnimation) {
        animator.start();
    }
}
```

**响应式布局避免重建**：使用 `ViewModel` 保存跨配置变更的数据，结合 `recreateOnConfigChanges`（Android 17+）减少 Activity 重建。不使用 `android:configChanges` 手动拦截配置变更——这个属性虽然能阻止重建，但需要手动处理所有资源切换，在现代 Android 开发中不推荐。

**减少 Layer 数量**：避免在多窗口场景中使用 `SurfaceView`（它会创建额外的 Layer），改用 `TextureView`（其内容绘制在 App 的主 Surface 上）或 Jetpack Compose 的原生渲染。虽然 `TextureView` 的渲染效率低于 `SurfaceView`，但在多窗口场景中减少 Layer 数量对 SurfaceFlinger 的压力缓解更重要。

## Android 16/17 大屏强制适配的渲染影响

Android 16（API 36）开始，在 smallestWidth ≥ 600dp 的设备上（包括大部分平板和折叠屏展开态），系统开始忽略 App 设置的屏幕方向锁定和尺寸限制。`screenOrientation`、`resizeActivity`、`minAspectRatio`、`maxAspectRatio` 这些 manifest 属性在 600dp+ 设备上不再生效。

对应到运行形态，所有 App 都可能进入可调整窗口尺寸的状态。即使 App 只声明了竖屏，它也可能在横屏大屏设备上以非全屏比例显示。

### 对渲染管线的具体影响

1. **Surface 尺寸不再固定**：App 的 Surface 尺寸可能随窗口大小变化而变化，不再像手机竖屏那样只有一个固定尺寸。每次尺寸变化都会触发 `Surface.change()` 和 Buffer 重新分配。

2. **配置变更频率增加**：大屏设备的配置变更更频繁——外接键盘/鼠标的插拔、窗口缩放、折叠屏的开合。如果每次都走 Activity 重建路径，渲染管线会频繁中断。

3. **Choreographer 帧节奏不稳定**：窗口尺寸变化导致 `requestLayout()`，如果在 `doFrame` 期间发生，布局重算会吃掉帧预算中的一大块时间。

`recreateOnConfigChanges`（Android 17）是 Google 对这个问题的官方解决方案。它把 Activity 重建的"重路径"变成了 `onConfigurationChanged()` 回调的"轻路径"，对渲染管线友好得多。配合 `ViewModel` 使用，配置变更前后的数据可以无缝过渡。

## 版本演进

| Android 版本 | 多窗口相关变化 | 对渲染的影响 |
|---|---|---|
| 7.0 (API 24) | 引入分屏和自由窗口模式 | SurfaceFlinger 首次需要同时合成多个 App Layer |
| 8.0 (API 26) | 画中画模式 | PiP Layer 悬浮在主 App 上方，需要持续合成 |
| 12 (API 31) | 小屏设备强制多窗口；非焦点 App VSync 节流 | 600dp 以下设备也进入多窗口；后台 App 渲染频率降低 |
| 14 (API 34) | 新增 `Activity.setShowWhenLocked()` 对多窗口的影响 | 锁屏 Layer 的合成优先级调整 |
| 16 (API 36) | 桌面窗口模式（外接显示器）；大屏强制适配 | 双显示输出；Layer 数量上限更易触达 |
| 17 (API 37) | `recreateOnConfigChanges` 减少重建；大屏限制扩展 | 配置变更不再中断渲染管线 |

## 常见问题与误区

**误区：多窗口下 App 渲染频率降低是 Bug**

Android 12+ 对非焦点 App 的 VSync-app 分发做了节流——从每帧一次降为每 2-3 帧一次。这是系统有意的优化，减少后台 App 的 GPU 占用。如果 App 依赖于精确的 VSync 时序（比如游戏），需要在 `onWindowFocusChanged()` 回调中感知焦点状态的变化。

**误区：`android:configChanges` 是优化配置变更的最佳方式**

`android:configChanges` 能阻止 Activity 重建，但它要求开发者手动处理所有资源切换——布局、尺寸、字符串、图标都要在 `onConfigurationChanged()` 中更新。在现代 Android 中，推荐使用 `ViewModel` + 自适应布局 + `recreateOnConfigChanges`（Android 17+）来处理配置变更，让系统自动完成资源切换，同时避免 Activity 重建。

**误区：多窗口下掉帧一定是 App 的问题**

多窗口场景下，SurfaceFlinger 的合成负载增加可能导致 SF 端掉帧（`SFDeadlineMissed`）。这种情况在 Perfetto 的 FrameTimeline Track 中表现为 SurfaceFlinger 的帧呈现延迟，而非 App 端的 `AppDeadlineMissed`。如果确认是 SF 端掉帧，App 侧能做的优化有限，更多需要系统层面调整（如减少同时可见的 Layer 数量、优化 HWC 合成策略）。

## 参考资料

- AOSP 源码路径：
  - SurfaceFlinger 合成循环：`frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp`
  - HWC 合成决策：`frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.cpp`
  - 多窗口管理：`frameworks/base/services/core/java/com/android/server/wm/WindowManagerService.java`
  - 配置变更处理：`frameworks/base/core/java/android/app/Activity.java`（`onConfigurationChanged`）
- 官方文档：
  - [Multi-window support](https://developer.android.com/guide/topics/large-screens/multi-window-support)
  - [Desktop windowing](https://developer.android.com/guide/topics/large-screens/desktop-windowing)
  - [Support different screen sizes](https://developer.android.com/guide/topics/large-screens/support-different-screen-sizes)
  - [Configuration changes handling](https://developer.android.com/guide/topics/resources/runtime-changes)
