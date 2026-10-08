---
title: 多窗口、PiP 与桌面模式渲染管线
chapter: '2.14'
section: '2.14'
status: finalized
applicable_versions: Android 7.0 (API 24) - Android 17 (API 37)
last_verified: '2026-08-24'
last_verified_against: AOSP android-17.0.0_r1 DisplayManager, WindowManager, WM Shell PiP, ViewRootImpl, HWUI, BLAST and SurfaceFlinger; Perfetto stdlib / FrameTimeline; kernel android17-6.18-2026-06_r6; current Android multi-window, PiP, desktop windowing and connected-display guidance
confidence: high
sources:
- type: official
  path: https://developer.android.com/develop/ui/compose/layouts/adaptive/support-multi-window-mode
- type: official
  path: https://developer.android.com/about/versions/16/behavior-changes-16
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-all
- type: official
  path: https://developer.android.com/about/versions/17/behavior-changes-17
- type: official
  path: https://developer.android.com/about/versions/17/release-notes
- type: official
  path: https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html
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
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayManagerService.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/LogicalDisplayMapper.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/LogicalDisplay.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/LocalDisplayAdapter.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/ExternalDisplayPolicy.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowContainer.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/window/WindowContainerTransaction.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/PictureInPictureParams.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/PictureInPictureUiState.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/pip/PipTaskOrganizer.java
- type: official
  path: https://developer.android.com/develop/ui/views/picture-in-picture
- type: official
  path: https://source.android.com/docs/core/display/multi-window
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/RenderThread.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
- type: material
  path: rendering_pipelines/S01_rendering_types_overview.md
- type: material
  path: rendering_pipelines/S06_multi_window_type.md
- type: material
  path: rendering_pipelines/S08_native_graphics_type.md
tags:
  - multiwindow
  - desktop-mode
  - split-screen
  - freeform
  - foldable
  - surfaceflinger
  - rendering
  - picture-in-picture
related_chapters:
- '2.9'
- '2.1'
- '1.19'
- '2.8'
- '7.2'
- '3.3'
- '13.1'
- '22.12'
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part1-fundamentals/ch02-rendering/2.29-Android-17-桌面模式窗口管理性能.md
- src/part2-performance/ch13-rendering-pipelines/03-android-view-multi-window.md
- src/part2-performance/ch13-rendering-pipelines/18-pip-freeform.md
---

# 多窗口、PiP 与桌面模式渲染管线

平板分屏、折叠屏展开态、PiP 和外接显示器是四类常见的多窗口场景。这些场景里，可见的 window/layer 数量、应用工作负载和 display 拓扑可能同时变化：SurfaceFlinger 要合成更多 layer、做更复杂的 composition decision（合成路径决策），而窗口 resize 的几何变化与新内容还可能在不同时刻到达。掉帧可能来自应用、WindowManager/WM Shell、SurfaceFlinger、GPU、Composer HAL 或显示硬件，所以我们要沿整条链路找责任方，而不是只盯着应用主线程。

排查的第一步，是分清分屏、PiP、desktop windowing（桌面窗口）与 connected displays（外接显示器）各自属于哪个显示会话，再建立 Display、Window、进程与 layer 的映射。映射准确之后，Perfetto 里的应用 jank、SurfaceFlinger jank、HWC 策略变化和 display present 才能归到正确的对象上。

## 多窗口形态和 display 会话

**分屏（Split-screen）** 从 Android 7.0（API 24）开始进入平台主线。两个应用同时可见，SurfaceFlinger 每一帧都要处理两组应用窗口，外加分割线和系统栏。对渲染分析来说，新增的是一整组持续变化的 layer 树，而不是多了一个应用进程那么简单。

**画中画（PiP）** 从 Android 8.0（API 26）扩展到小屏设备。PiP 窗口面积不大，但里面的视频帧或地图帧往往持续提交。主窗口和小窗同时刷新时，SurfaceFlinger 要在前景主窗口之上继续处理一组持续更新的小窗 layer。

**Freeform/desktop windowing** 与“手机连接外接显示器”是两类能力。桌面窗口指兼容设备上的可调整大小窗口：用户可以同时打开多个应用窗口，底部有 taskbar（任务栏），窗口顶部有标题栏和最小化、最大化控件。外接显示器能力关注的则是设备接上外屏后，桌面会话如何分布到两块屏幕。

四类场景的会话形态与渲染观察点整理如下：

| 场景 | 公开边界 | 会话形态 | 渲染观察点 |
|---|---|---|---|
| Split-screen | Android 7.0（API 24）平台支持 | 一块屏幕里并排两个可见应用窗口 | 同时可见 layer 增多，分割线和系统栏常驻 |
| PiP | Android 7.0 在部分设备提供，Android 8.0（API 26）扩展到小屏 | 一块屏幕里包含主窗口和持续更新的小窗 | 小窗经常持续提交 buffer，并与主窗口叠加 |
| Freeform/desktop windowing | 大屏或兼容设备上的可调整大小窗口 | 一块或多块屏幕里的多个可调整大小窗口 | layer 数量和窗口遮挡关系更复杂，composition decision 更频繁 |
| 手机和 connected display | 手机连接外接显示器 | 手机保持原有状态，外屏启动独立 desktop session（桌面会话），形成两个显示会话 | SurfaceFlinger 同时驱动两个 display，会话内容彼此独立 |
| desktop windowing 设备和外接显示器 | 平板等 desktop windowing 设备连接外屏 | 桌面会话跨两块屏幕扩展，窗口和光标可跨屏移动 | 仍是同一套桌面会话，但 display 范围更大、像素更多 |

```mermaid
flowchart LR
    S["单个物理 Display"] --> SS["Split-screen<br/>两个 Task 同屏"]
    S --> PP["PiP<br/>主窗口 + pinned window"]
    S --> DW["Desktop windowing<br/>多个可移动 Task"]
    CD["Connected displays"] --> PH["手机内屏会话"]
    CD --> EX["外屏桌面会话"]
    TD["支持 desktop windowing 的平板 + 外屏"] --> WS["同一桌面 workspace 跨两个 Display"]
```

这张图描述的是产品会话，和进程、渲染线程的拓扑是两回事：两个可见窗口可能属于同一进程，也可能属于不同进程；应用窗口移动到外屏后，它的 display、密度、刷新率、HDR 能力和窗口尺寸都可能变化。

## Display 对象与显示会话的映射

多窗口的窗口组织主要由 WindowManager 和 WM Shell 负责；显示设备的发现、logical display（逻辑显示）策略和投影则归 DisplayManagerService（DMS，显示管理服务）管理。动手排查前，我们先要分清五类对象：

| 对象 | 所在层 | 主要职责 |
|---|---|---|
| physical display/`PhysicalDisplayId` | SurfaceFlinger/Composer | 物理连接、mode、VSync、HWC present |
| `DisplayDevice` | DMS adapter（适配）层 | 表示本地、虚拟、Wi-Fi、overlay（叠加）等显示设备 |
| `LogicalDisplay`/`displayId` | DMS policy（策略）层 | 向系统暴露逻辑显示、layer stack（图层栈）、投影和 display group（显示组） |
| `DisplayContent` | WindowManager | 按 `displayId` 组织 Task、Window、Insets、focus（焦点）与 transition（窗口过渡） |
| CompositionEngine Output | SurfaceFlinger | 为每个目标输出构造可见 layer 集合并与 HWC 协商 |

`LogicalDisplay.java` 的类注释写得很清楚：logical display 与 display device 是相互独立的概念，映射可以是多对多，也可能没有直接关系。镜像、虚拟显示和 display projection 都会打破“一块 logical display 对应一块物理屏”的简化模型。所以排查时要分别记录 DMS 的 `displayId`、SurfaceFlinger 的 physical display ID、layer stack 和 HWC display handle（显示句柄），把每个观察结果挂到正确的对象上。

### physical display 的发现与 logical display 的建立

`LocalDisplayAdapter.registerLocked()` 从 SurfaceFlinger 枚举 physical display ID，再用 `tryConnectDisplayLocked()` 读取 token（对象标识）、静态信息、动态 mode 信息和 desired mode specs（期望显示模式约束）。新设备先成为 `LocalDisplayDevice`，再由 `DisplayDeviceRepository` 通知 `LogicalDisplayMapper` 建立或更新 logical display——hotplug（热插拔）事件就是这样进入系统显示对象的。

`mDevices.size() == 0` 只决定 `LocalDisplayDevice` 的 `mIsFirstDisplay`，影响首屏资源和背光等初始化。默认逻辑显示还要经过 `LogicalDisplayMapper` 的 layout（设备布局）与 `FLAG_ALLOWED_TO_BE_DEFAULT_DISPLAY` 规则；`displayId = 0` 归谁，要看这些规则的结果，单凭枚举顺序是推不出来的。

下图用于串起物理显示热插拔到 SurfaceFlinger output 的控制路径：

```mermaid
flowchart LR
    HP["SurfaceFlinger hotplug / physical display"] --> LDA["LocalDisplayAdapter"]
    LDA --> DDR["DisplayDeviceRepository"]
    DDR --> LDM["LogicalDisplayMapper"]
    LDM --> LD["LogicalDisplay / display group / layer stack"]
    LD --> DMS["DisplayManagerService listener"]
    DMS --> WMS["WindowManager traversal"]
    WMS --> SCT["SurfaceControl.Transaction"]
    SCT --> SF["SurfaceFlinger outputs"]
```

箭头表示对象建立与状态传递的顺序；每一步未必都在同一帧完成，logical display 与 physical display 之间也没有固定的一一对应。

### `DeviceState` 与 desktop windowing mode 的分工

`LogicalDisplayMapper.setDeviceState()` 处理折叠、展开、lid（上盖）、dock（扩展坞）这类可能改变物理显示布局的设备状态。它会在 `mSyncRoot` 锁保护下记录 pending state，按需临时关闭参与切换的 display，并依据 `DeviceState` property 决定 wake/sleep；完成条件迟迟不满足时，延迟消息会强制结束 pending transition。

普通的 freeform/desktop windowing 是 Task/Window 层面的 windowing mode（窗口形态），走不到 `LogicalDisplayMapper.setDeviceState()` 这条路径。只有 dock、lid 或厂商硬件状态真的改变 display layout 时，两条路径才会在同一场景中相遇。

另外，冷启动 trace 里仍可能出现 fold/unfold（折叠/展开）事件——设备状态可以暂存到 boot completed（启动完成）之后再应用。

### 外接显示策略与扩展桌面的启用条件

`ExternalDisplayPolicy.isExternalDisplayLocked()` 用 `Display.TYPE_EXTERNAL` 识别外接 logical display，并负责启停、thermal 限制、连接事件和统计。Android 17 起，`isDisplayContentModeManagementEnabled()` 为真时，`isExtendedDisplayAllowed()` 不再依赖开发者选项；不过“允许 extended content mode（扩展内容模式）”只是打开了门，连接后是否自动进入桌面扩展，还要看 layout、boot 阶段、用户确认、thermal 状态和设备配置。

应用侧要判断外屏是否可用，只能在运行时查询 `DisplayManager`、当前 activity context 与 window metrics，拿 Android 版本号去推导是靠不住的。

### DMS traversal 如何进入显示 transaction

`mSyncRoot` 的源码注释是“保护 DMS 的大部分状态”，同时也有相当一部分显示工作在这把锁之外完成。`scheduleTraversalLocked()` 用单个 `mPendingTraversal` 合并重复请求，Handler 收到 `MSG_REQUEST_TRAVERSAL` 后调用 `WindowManagerInternal.requestTraversalFromDisplayManager()`。随后 WMS 回调 DMS 的 `performTraversal()`，把 logical display 的 layer stack、orientation（方向）、projection 和 Surface 状态写进对应的 `SurfaceControl.Transaction`；desired mode specs 则由 `ModeRequestManager` 收集后交给 display adapter 批量应用。

这条链路能说明 DMS 变更会并入 WMS/display traversal（遍历与状态提交），但它给不出“热插拔后的下一个 VSync 就完成”的保证，工程上要按多帧窗口来预期。

`android.display` 线程上出现长 slice 只能说明该线程繁忙；要判断 `mSyncRoot` 竞争，还要结合 monitor contention（监视器锁争用）、线程调度，以及锁当时由谁持有。Android 17 的 lock-free `MessageQueue` 也不会拆掉 DMS 自身的 `mSyncRoot`。

### DMS 与 SurfaceFlinger 的观察面

- `dumpsys display`：查看 logical display、display group、DisplayDevice、当前 layout、device state 和 power controller。
- `dumpsys SurfaceFlinger` 与 Winscope：查看 physical/virtual output、layer tree、projection 与每个 output 的 composition 状态。
- `surfaceflinger_layer`：提供全局 layer snapshot（图层状态快照），没有 `display_id` 列。
- `android_surfaceflinger_display`：提供同一 snapshot 中的 display 信息，但缺少通用的 layer 外键，两张表之间没有现成的关联字段。
- `android_surfaceflinger_transaction`：包含 `layer_id` 与 `display_id`，适合确认某次 transaction（状态事务）的目标；最终的 output-layer 可见性还要另行确认。

多屏归属要结合 Winscope 的 output tree、display transaction、layer parent chain（图层父子链）和目标时间片一起确认。仅按 `snapshot_id` 连接两个表，会把 snapshot 中的所有 layer 同时归给每一个 display，归属判断要靠上面几项交叉确认。

## Window、线程与 Surface 拓扑

多窗口未必对应多进程。一个进程可以有多个顶层 Window，每个 Window 有自己的 `ViewRootImpl`、窗口 Surface 和 BLAST buffer 流；这些窗口仍可能共享 UI Looper 和 HWUI RenderThread。哪些东西共享、哪些独立，直接决定瓶颈长在哪里：

| 证据 | 执行拓扑 | 性能含义 |
|---|---|---|
| 同一 pid（进程 ID）、同一 UI tid（线程 ID）、多个 ViewRoot | 共享 UI Looper（消息循环）与同一个 ThreadLocal（线程局部）`Choreographer` | 到期的 traversal callback（界面遍历回调）在同一线程串行执行 |
| 同一 pid、多个硬件加速窗口 | 每个窗口有 renderer/CanvasContext（渲染上下文），共享进程级 HWUI RenderThread | 一个窗口的 DrawFrame、dequeue 或 fence wait 可能推迟另一个窗口 |
| 不同 pid | UI Looper、Choreographer 与 RenderThread 分离 | 应用 CPU 工作可以独立，仍共享目标 Display 的 SF/HWC/GPU/带宽 |
| 不同 `displayId` | 分属不同 WMS `DisplayContent` 与 SF output | mode、deadline、color、HWC 能力和 present fence 要分别分析 |

`Choreographer` 在源码中是 ThreadLocal（线程局部），按线程而非按 Window 存在；`RenderThread::getInstance()` 提供的则是进程级 HWUI RenderThread。共享线程，却仍各用各的 BufferQueue：每个应用窗口独立提交 buffer，有自己的 acquire/release 关系和 layer identity（图层标识）。

判断时按 `pid/tid/ViewRootImpl/WindowState/layerId/displayId` 建表。屏幕上的两个 pane（窗格）也可能只是同一 Activity 里的双栏 View，这时只有一个 ViewRoot 和一条应用窗口 buffer 链路，按单窗口管线分析即可。

### 先确认画面是否对应多个 Window

同一 Activity 内的双栏 View、`SlidingPaneLayout` 或 Compose pane 可能只有一个 `ViewRootImpl` 和一条 App Window buffer 链路。比较可靠的多窗口证据是：

- 多个顶层 `ViewRootImpl`；
- WMS 中存在不同的 `WindowState`、Window token、Task 或 TaskFragment；
- 各窗口拥有独立的 App Window Surface、BLAST 提交链和 SF buffer layer；
- 窗口可分别映射到不同的 `pid`、UI `tid` 或 `displayId`。

系统栏、壁纸、输入法、dim layer 和 transition leash 也会增加 SF layer。layer 数量本身说明不了应用是否创建了多个 Window，要同时核对 WMS 与 SF 两棵树。

### Choreographer 的归属单位是线程

`Choreographer` 用 ThreadLocal 保存实例，每个线程一个。多个 `ViewRootImpl` 建在同一个 UI Looper 上时，拿到的是同一个 Choreographer，并各自向 `CALLBACK_TRAVERSAL` 队列提交 traversal 回调。

同一批次中已到期的回调会在 UI 线程上按队列顺序执行；批次结束后才加入的回调进入后续 frame。应用也可以在其他带 Looper 的线程上创建 Choreographer，所以判断单位是 Looper/tid，只看 pid 会漏掉这类窗口。

### 每个窗口状态与 buffer 独立

同进程的多个顶层 Window 仍各有：

- `ViewRootImpl`、保存窗口附着信息的 AttachInfo、Insets，以及标记待重绘区域的 dirty state；
- `ThreadedRenderer` / `CanvasContext`，即该硬件加速窗口的渲染入口与上下文；
- App Window Surface、BLAST/BufferQueue，也就是应用向 SF 交付 buffer 的队列；
- SF buffer layer、表示新 buffer 到达的 `BufferTX`，以及 buffer 可复用时触发的 release callback。

共享主线程和 RenderThread，并不改变每个窗口各自的 buffer 周期：A 的 release fence 直接决定 A 的旧 buffer 何时可复用；A 在共享 RenderThread 上一旦等待，排在后面的 B 也会被推迟。

### 跨进程窗口共享的设备资源

不同进程各有 UI Looper、Choreographer 待处理帧状态、RenderThread、App Surface、GC 和处理 Binder 调用的线程池，并通过各自的 display event connection 接收 VSync 预测，应用任务不会直接排在同一线程。但在同一 Display 上，它们仍共享：

- SurfaceFlinger 处理 transaction 和 layer 的时间预算；
- CompositionEngine，以及由 RenderEngine 执行的 CLIENT composition（客户端合成）；
- HWC 的 plane（硬件叠加层）、scaler（缩放器）、带宽和 protected path（受保护内容显示路径）；
- display mode、color mode、present deadline 和显示面板；
- GPU、CPU、内存带宽、温控与功耗等设备资源。

所以即使 App A 和 App B 的 `doFrame()` 都正常，Shell transition、CLIENT composition、HWC 或 Display 阶段仍可能让目标 DisplayFrame 迟到。

### 多 Display 要分别计时

每个 Display 都有自己的可见 layer 集合、mode、HWC output 与 present fence。窗口从内屏移到外接屏后，解释外屏延迟要用外屏自己的 FrameTimeline 和 present fence，默认屏的数据套不过去。

Output 指 SurfaceFlinger 面向某个 Display 构造的合成输出，同一个 layer 还可能经镜像、virtual display（虚拟显示）或投屏进入多个 Output。检查延迟前先确认目标 Display 的 output layer state，全局 layer 存在与否只是第一步。

## Perfetto 与 dumpsys 的观察面

多窗口分析里有两类查询错误最常见：用了并不存在的表名，以及把某个版本里的 slice 名当成平台通用名称。我们按下面的步骤建立可复用的查询路径。

### 0. 建立 Window 表

| 字段 | 记录内容 |
|---|---|
| 归属 | uid（应用身份）、pid、package，以及 Activity/Dialog/Popup/PiP/SystemUI 类型 |
| 执行 | UI tid/Looper、Choreographer、RenderThread tid 和 ViewRoot identity（实例标识） |
| WMS | displayId、Task/TaskFragment、WindowToken/WindowState、windowing mode 和 bounds |
| SF | container/leash/buffer layer id、父节点、Z、crop 和可见性 |
| Buffer | BLAST/BufferQueue、`BufferTX`、frame number 和相关 fence |
| FrameTimeline | SurfaceFrame/DisplayFrame token、layer 名称和 present type |

这张表能识别同名窗口已经重建、Dialog 与主窗口共享线程、PiP 位于另一个 Display 等情况，避免把名称相同的 slice 当成同一对象。

### 1. 列出当前 trace 中的 SurfaceFlinger slice 名

`doCompose` 这类名字要先验证再当过滤条件。第一步是列出当前 trace 中 SurfaceFlinger 线程实际存在的 slice 名，再从中筛选合成相关项：

```sql
SELECT DISTINCT slice.name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread ON thread_track.utid = thread.utid
JOIN process ON thread.upid = process.upid
WHERE process.name GLOB '*surfaceflinger*'
  AND thread.tid = process.pid
ORDER BY 1;
```

版本升级、厂商裁剪或 trace config（采集配置）差异造成的 slice 名称差别，在这一步就能直接发现。

### 2. layer 快照表要使用真实 schema

Perfetto stdlib（标准函数库）文档中，SurfaceFlinger layer snapshot 对应的表是 `surfaceflinger_layers_snapshot` 和 `surfaceflinger_layer`；`surfaceflinger_layers` 这张表并不存在。这里的 schema 指 trace 数据库的表与字段定义。可直接执行的查询如下：

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

这个查询列出某个 snapshot 中的可见 layer、名称与 HWC composition 类型。Perfetto stdlib 的 `surfaceflinger_layer` 表没有 `display_id` 列，connected display 的 trace 里 `WHERE l.display_id = 0` 这样的条件也就无从写起。区分 display 时，先在 Winscope 的 output tree（输出树）里确认目标输出，再用 `android_surfaceflinger_transaction` 的 `layer_id/display_id` 配合相邻 transaction 定位。`android_surfaceflinger_display` 只有 display 记录，同一 snapshot 的全部 layer 并不会因此自动归到该 display。

### 3. 完整记录 FrameTimeline 卡顿名称

FrameTimeline 里，应用侧和 SurfaceFlinger 侧至少要分三类：

- `AppDeadlineMissed`：应用没有按时交帧。
- `SurfaceFlingerCpuDeadlineMissed`：SurfaceFlinger 主线程没有在 deadline（截止时间）前完成 CPU 侧工作。
- `SurfaceFlingerGpuDeadlineMissed`：CPU 侧工作已经推进，GPU composition 没有按时完成。

多窗口场景下，优先核对后两类。窗口、display 一多，先把 SurfaceFlinger 侧和应用侧的 deadline miss 分开，再决定是检查应用主线程、RenderThread、图片上传、视频解码，还是沿 SurfaceFlinger、HWC 与 GPU composition 继续向下。

一套可复用的顺序是：在 `actual_frame_timeline_slice` 中找到异常 SurfaceFrame/DisplayFrame token，对齐目标进程的 `doFrame`、RenderThread 与 buffer transaction；取最接近异常时刻的 layer snapshot，确认 output、可见 layer 和 composition type；再检查 SurfaceFlinger main thread、GPU fence、Composer/HAL 与 present。这样就能区分单个窗口晚交帧与整屏合成延迟。

## 共享线程上的串行执行

多窗口最常见的瓶颈，是同一 Looper 或 RenderThread 上的串行执行；跨进程资源竞争、SF/HWC 合成和 Display 输出同样会造成延迟，所以应用线程之外的位置也要纳入排查。

### UI callback 串行

多个 ViewRoot 位于同一 UI 线程时，到期的 traversal 依次执行。Window A 的输入处理、动画、Insets、relayout 或 `performTraversals()` 占住 CPU，队列里的 Window B 就要跟着等。

还要注意，一个 `doFrame` 未必包含两次完整 traversal：某个 Window 没有 dirty 或 layout 工作时可能不绘制，两个回调也可能分进不同 frame。读 trace 时按 ViewRoot/Window 实例标记每段工作，比数 traversal 次数可靠。

### RenderThread 队列共享

`RenderThread::getInstance()` 提供进程级 HWUI RenderThread。每个硬件窗口各有 CanvasContext，但任务进入同一 RenderThread 系统：

- A 的 CPU 渲染准备耗时长，B 的任务只能排队；
- A 的 `dequeueBuffer()` 或 release fence 等待占住 RenderThread 时，B 的开始时间随之后移；
- A 提交大量 GPU 工作后，B 的 CPU 任务再短，也可能受 GPU 队列与带宽影响。

`DrawFrameTask::run()` 在 `syncFrameState()` 之后，会根据 `info.prepareTextures` 决定是否先解除 UI 线程的等待。这时 UI 线程可能已经在处理 B，RenderThread 却仍在绘制 A。主线程回调、RenderThread 任务和 GPU 工作是三段不同的时间线，排队与依赖要分别判断。

### GL 与 Vulkan 后端的差异

SkiaGL 可能涉及不同 EGLSurface 的 current 状态、buffer swap 和 GL context；SkiaVulkan 用的是另一套 surface、queue 与同步路径。仅凭“两个窗口”推不出固定的 `eglMakeCurrent` 开销，Vulkan 的上下文、队列切换成本同样要实测。

trace 显示窗口切换附近变慢时，先核对当前 HWUI backend（后端）、对应的 context/surface、GPU queue、fence 和厂商驱动 slice，再下结论。

### 跨进程窗口的竞争位置

跨进程窗口各有 App RenderThread，但仍会在 CPU 调度、GPU 队列、内存和同一 Display 的 HWC 阶段相遇。瓶颈可能落在任一应用进程，也可能落在 SurfaceFlinger、HWC 或底层设备资源。正确顺序是先分别完成每个窗口的应用侧判断，再看同一 Display 的 geometry、SF/HWC 与 present。

## 桌面窗口的 Shell 路径

桌面模式的 caption（标题栏）、最大化菜单、拖拽与 resize handle 由 SystemUI 进程中的 WM Shell window decoration（窗口装饰）子系统管理，与应用 `PhoneWindow` 的 `DecorView` 无关。一扇桌面窗口至少要区分应用窗口、Task/container leash（动画期间承载容器的临时 Surface）、Shell decoration 与 resize 过渡层；它们可能属于不同进程、Surface 和帧循环。

`DesktopTasksController` 通过 `WindowContainerTransaction`（WCT，窗口容器状态事务）改变 task bounds、windowing mode、层级和 display 归属。后台 task 进入桌面、运行中 task 转为 freeform、freeform 最大化/还原和退出桌面，走的是不同 transition；“画面已经开始动画”距离 WMS active bounds、应用 configuration 和新尺寸 buffer 全部就位，还有一段时间。

Android 17 的 window decoration 可以复用 `ViewHost`，减少 caption 反复创建的成本；decoration 仍独立于应用 View 树，Shell host 有自己的 ViewRoot/Surface 生命周期，应用内容走独立的 BLAST buffer。我们排查 caption 卡顿时先看 SystemUI/Shell 线程；排查内容重布局则回到目标应用的 UI/RenderThread。

拖拽和 resize 分两类：

- 只移动位置时，Shell 直接更新 task surface 的 position，避免每次 pointer move 都触发应用 configuration；
- fluid resize（实时调整大小）持续改变 leash/bounds，等应用产出匹配新尺寸的内容；veiled resize（遮罩式调整大小）先移动遮罩或预览，结束时提交最终 bounds。

fluid resize 期间，几何先到而新 buffer 未到时，旧内容可能被暂时缩放；veiled resize 则把成本推迟到结束点。排查时要记录当前策略、pointer/input、WCT、transition start/finish transaction、应用 relayout/traversal、BLAST buffer 尺寸和 display present，把“模糊”统一归因于 GPU sampling（纹理采样）并不可靠，对照这些记录再下判断。

WMS 内部 `BLASTSyncEngine` 与 transition handler（过渡处理器）协调参与同一过渡的 WindowContainer 和 surface transaction：start transaction 建立起始视觉状态，finish transaction 恢复或提交最终状态。未注册的 Camera、codec、SurfaceView producer 不会因为同屏就自动参加该同步协议。

## WMS geometry 与应用 buffer 是两条输入

窗口 resize、PiP 和 Shell transition 同时牵动管理状态、layer 几何属性和应用内容，三路输入各走各的通道：

| 输入 | 典型对象 | 改变什么 |
|---|---|---|
| `WindowContainerTransaction` | Task、TaskFragment、WindowContainer | bounds、windowing mode、层级与 reparent（更换父容器）请求 |
| `SurfaceControl.Transaction` | container、transition leash、window layer | position、crop（裁剪）、变换参数、alpha（透明度）、Z 轴顺序、visibility |
| 应用 BLAST transaction | 应用窗口 buffer layer | 新 buffer、acquire fence、frame number |

Shell transition 常把 Task 或 Activity Surface 临时 reparent 到 leash 上执行动画。此时 position/crop 可能落在 leash，应用的新尺寸 buffer 则由 BLAST 单独到达。新 geometry（几何属性）配旧 buffer 可能是过渡策略的一部分；要对齐 WCT、leash transaction、应用 relayout/traversal 和 buffer 选择，才能判断黑边、拉伸或跳变来自哪条路径。

`ViewRootImpl.performTraversals()` 只在首帧、尺寸、可见性、Insets（系统栏等占用区域）或 `LayoutParams` 等条件变化时才进入 `IWindowSession.relayout()`，稳定的绘制帧里没有这一步。所以稳定绘制帧里没有 relayout slice 时，应用 draw 慢的原因要到 WMS 之外找。

WMS 内部的 `BLASTSyncEngine` 可以等待一组 WindowContainer 的 draw/transaction；公开的 `SurfaceSyncGroup` 面向应用与嵌入 Surface。两者都只等已注册的参与者，Camera、codec 或游戏引擎的下一业务帧要另外建立同步。

### 从回调队列到 Display present

下面的时序图说明 A/B 的共享执行与 C 的独立执行：

```mermaid
sequenceDiagram
    participant UI as Process A UI Looper
    participant CH as ThreadLocal Choreographer
    participant A as ViewRoot A
    participant B as ViewRoot B / Dialog
    participant RTA as Process A RenderThread
    participant C as Process C UI / RenderThread
    participant WMS as WMS / WM Shell
    participant SF as SF FrontEnd / CompositionEngine
    participant HWC as HWC / Composer

    A->>CH: post traversal A
    B->>CH: post traversal B
    CH->>UI: doFrame callback phases
    UI->>A: traversal A
    A->>RTA: syncAndDrawFrame A
    RTA-->>UI: unblock when sync boundary permits
    UI->>B: traversal B
    B->>RTA: syncAndDrawFrame B

    par Process A window buffers
        RTA->>SF: buffer transaction A
        RTA->>SF: buffer transaction B
    and Process C window buffer
        C->>SF: PiP buffer transaction C
    and Window geometry
        WMS->>SF: geometry / leash transaction
    end

    SF->>SF: state / hierarchy / snapshot
    SF->>SF: select new or retained content per window
    SF->>HWC: target Display visible layer set
    alt can skip validate
        SF->>HWC: presentOrValidate
    else normal path
        SF->>HWC: validate
    end
    opt CLIENT composition
        SF->>HWC: setClientTarget + acquire fence
    end
    opt not already presented
        SF->>HWC: present
    end
    HWC-->>SF: per-display present fence + per-layer release fences
```

图中只表达任务和状态的关系，A/B 每一帧未必都同时绘制。`PresentSucceeded` 表示 HWC 调用已经进入 present 分支并保存相关 fence；显示面板有没有扫描到这一帧，它本身说明不了。

## SurfaceFlinger 与 HWC 按 Output 组织合成

SurfaceFlinger FrontEnd（前端状态层）接收所有窗口、Shell/WMS 几何属性和 buffer transaction，更新 layer hierarchy（图层层级）与 snapshot；CompositionEngine 再按 Output/Display 构造可见 layer 集合。同一个 layer 还可能因镜像或 display projection 落进多个 output，所以只确认全局 layer 存在远远不够。

多窗口的成本主要来自三类变化：

1. 可见 layer、leash、caption、dim（变暗遮罩）、IME 与 SystemUI layer 增多；
2. scale、rotation、alpha、HDR/SDR、protected content（受保护内容）等组合让 HWC strategy 更复杂；
3. 多个 output 带来各自的 mode、可见 layer 集合、client target 和 present。

窗口变多未必切换到 CLIENT composition，单个复杂窗口也可能触发 GPU 合成。要比较的是相邻帧整个 output 的 layer 属性和 DEVICE/CLIENT 结果，layer 数量换算不成 GPU 开销。

### fence 要按 buffer 与 Display 分层

| 信号 | 粒度 | 能证明什么 |
|---|---|---|
| acquire fence | 一块 producer buffer | producer 何时写完，consumer 何时可读 |
| release fence | 被消费的 layer/buffer | 旧 buffer 何时可以复用 |
| present fence | 一次 Display present | 该 output 的 present 工作何时到达 Android 显示栈完成边界 |

present fence 不属于某个 Window：内屏与外屏各有自己的 present 结果；刷新率不同时，60 Hz 的帧预算也解释不了 120 Hz output。FrameTimeline 中出现 SurfaceFlinger jank 后，先通过 DisplayFrame token、目标 output 和相邻 display 状态确定归属，再判断另一块屏有没有受到影响。

### 多窗口开销的实测方法

overlay plane（显示硬件平面）、scaler、分辨率、刷新率、内存带宽和厂商 Composer 都会改变结果，“每增加一个窗口固定多耗时几毫秒”“必然增加多少 PSS（按共享比例分摊后的驻留内存）”这类通用结论得不出来。可复用的做法是在同一设备上固定场景，记录每个 output 的可见 layer、composition type、FrameTimeline、GPU/fence 和 present，前后对比。

## PiP 与 Freeform 的特殊边界

PiP 和 Freeform（可自由调整的窗口）仍走常规的应用绘制链路：普通 View 由 ViewRoot/HWUI 生产窗口 buffer，视频或 Camera 的独立 Surface 由各自的 Producer（内容生产方）供帧。变化主要发生在 Task/Window bounds、transition leash、layer geometry 和同屏合成策略上。

### PiP 进入流程与参数

应用请求进入 PiP 后，WindowManager 把目标 Task 切换到 pinned windowing mode（画中画专用窗口模式）。WM Shell 取得 Task leash，在动画过程中持续更新 position、crop、scale、round 和 alpha，结束时提交最终的 WindowContainerTransaction。系统可以先对已有内容做缩放和裁剪，无须等应用在每个动画采样点生成新 buffer。视频以 24/30 fps 供帧、Display 以 60/90/120 Hz present 时，同一视频 buffer 被多次使用是正常行为。

`PictureInPictureParams` 会直接改变 transition 质量：

| 参数或回调 | 正确边界 |
| --- | --- |
| `sourceRectHint` | 指出切换到小窗后仍可见的源内容区域；它只为进出动画提供取景提示，不是持续裁剪内容的 API |
| `setAutoEnterEnabled(true)` | API 31+ 中，用户通过手势回到桌面时，系统可更早获知进入 PiP 的意图，不必依赖较晚的生命周期回调 |
| `setSeamlessResizeEnabled(true)` | 适合视频等可连续缩放的内容；复杂 UI 应明确设为 `false`，并验证 snapshot 或 cross-fade（交叉淡入淡出）的效果 |
| `onPictureInPictureUiStateChanged()` | target API 35+ 可在进入动画开始时隐藏标题、推荐卡片等不需要出现在小窗中的 UI |

Android 17 r1 中，未设置的 `autoEnterEnabled` 返回 `false`。`seamlessResizeEnabled` 的注释与实际调用路径有差异：getter 遇到空值返回 `false`，`PipTaskOrganizer` 又直接用该 getter 决定 resize 结束时是否执行 snapshot cross-fade。

这些隐式默认值不该被依赖：视频场景明确传 `true`，复杂 UI 明确传 `false`，并在旋转、折叠或内容 bounds 变化后更新 params。

PiP 的常见风险：leash geometry 已变而新 buffer 未到；圆角、alpha、HDR 的组合改变 HWC strategy；旧的大尺寸 buffer 尚未 release，新尺寸 buffer 已开始分配；进入小窗后 Producer 仍维持不必要的高分辨率或高帧率。SurfaceFlinger 缩小 layer 只改变合成时的几何，Producer 的分辨率和供帧节奏并不会跟着变。

### Freeform resize：分开 geometry 与 buffer

为便于对照，把旧 geometry 与旧 buffer 记为 `G0/B0`，新 geometry 与新 buffer 记为 `G1/B1`：

| 组合 | 视觉结果 |
| --- | --- |
| `G0 + B0` | 旧窗口仍一致 |
| `G1 + B0` | 旧内容被缩放、裁剪或以 letterbox（留黑边）方式适配；这可能是过渡期的预期结果 |
| `G1 + B1` | 新几何与新内容一致 |
| `G0 + B1` | 新内容落在旧几何中，通常属于需要避免的时序错配 |
| snapshot / starting layer | 系统提供的替代内容覆盖应用重绘间隙 |

WMS 的 `BLASTSyncEngine` 收集已加入 sync group 的 WindowContainer transaction；应用窗口的 `BLASTBufferQueue` 把下一块 buffer 封装进 SurfaceControl transaction；API 34+ 的 `SurfaceSyncGroup` 让应用和嵌入式 Surface 协调提交。三者都做同步，参与对象、调用权限和 ready 条件各不相同。

## 三个常被过度解读的 Android 17 变化

### lock-free MessageQueue 的作用范围

Android 17 为 target SDK 37 及以上的应用启用 lock-free `MessageQueue`（DeliQueue）。Google 内部 beta trace 报告的 missed-frame（错过截止时间的帧）降幅，归因于 MessageQueue monitor contention 的减少。这笔收益也说明不了 SurfaceFlinger transaction、WMS `mGlobalLock` 或 DMS `mSyncRoot` 的锁情况，后者的分析仍要单独做。

### 桌面窗口能力的查询方式

官方 desktop windowing 文档描述的是 caption/header insets（标题栏占用区域）、可调整大小窗口、taskbar 和多实例交互；`PROPERTY_SUPPORTS_MULTI_INSTANCE_SYSTEM_UI` 从 Android 15 开始提供。文档里没有通用的 `applyCachedState` Perfetto slice，“SurfaceControl 属性持久化缓存”这样的平台结论也立不住。设备是否启用 desktop windowing、connected display content mode 和多实例入口，都要在运行时确认。

### 16 KB page size 与多窗口的关系

16 KB page size（内存页大小）影响 native 库兼容性和进程内存布局，并不会带来另一条多窗口渲染管线。评估多窗口驻留内存时，可用 `linux.process_stats` 看进程 RSS（驻留内存）与交换空间，再结合系统 `MemAvailable`、`android.memory.process`、GPU memory、`dumpsys meminfo` 和 LMK（低内存终止）事件判断。

只看到 `MemAvailable` 下降，还判断不出系统已超过后台回收能力；要确认进程重要性、RSS/swap、GraphicBuffer/GPU memory、缓存回收和是否发生 LMK。优化对象应是已确认不再需要的纹理、离屏 buffer、解码输出或缓存；仅凭失去 top-resumed（顶层恢复）状态，还不足以决定释放可见窗口仍在使用的资源。

## 配置变更与大屏适配

### `recreateOnConfigChanges` 的公开语义

`recreateOnConfigChanges` 的方向和 `android:configChanges` 相反：`configChanges` 表示这类变化由应用自行处理，系统不重建 Activity；`recreateOnConfigChanges` 表示即使系统默认不重建，这类变化仍要重新走完整的 Activity 生命周期。

它也不是所有配置变化的通用重启开关。Android O 之后，`mcc|mnc`（移动国家码与移动网络码）默认不再触发 Activity 重建，应用可以用 `recreateOnConfigChanges` 显式要求这两类变化触发重建；API 37 又把 touchscreen、keyboard、keyboardHidden、navigation、colorMode 变化纳入默认不重建范围。依赖完整重建来加载资源的应用，要在 manifest（应用清单）里显式声明。

窗口尺寸、方向和屏幕 layout 这类多窗口场景中的高频变化，仍要通过 `android:configChanges`、`onConfigurationChanged()`、状态保存和系统实际生命周期回调处理；折叠屏、桌面模式的尺寸变化开关，`recreateOnConfigChanges` 承担不了。

### Android 16 与 17 的大屏规则

大屏多窗口的规则从 Android 12（API 31）起逐步收紧，直接影响应用形态约束的两步落在 Android 16（API 36）和 Android 17（API 37）。

Android 12（API 31）把 multi-window 变成 large-screen（大屏）上的标准行为：大屏设备会让所有应用进入 multi-window 流程，`resizeableActivity="false"` 失去绝对开关的地位，适配不了的应用进入 compatibility mode（兼容模式）。

Android 16（API 36）进一步把大屏规则扩展到 `sw >= 600dp`，其中 `sw` 指 smallest width（最小宽度）资源限定，`dp` 是密度无关像素。对 `targetSdkVersion >= 36` 的应用，平台会忽略 `screenOrientation`、`android:resizeableActivity="false"`、`minAspectRatio`、`maxAspectRatio`，以及 `setRequestedOrientation()` 与 `getRequestedOrientation()` 这类限制窗口形态的接口。

文档同时提供了临时退出选项：

```xml
<activity ...>
    <property
        android:name="android.window.PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY"
        android:value="true" />
</activity>
```

这项退出配置只在 API 36 过渡期有效，应用面向 API 37 后它就失效了：Android 17（API 37）会直接忽略 `sw >= 600dp` 设备上的方向、宽高比和 resizability 限制。

这条规则管不到 `sw < 600dp` 的屏幕；按 `android:appCategory` 标记的游戏也有例外，系统仍尊重用户为单个应用选择的宽高比。设备厂商还可以调整多窗口行为，所以测试记录要包含 target SDK、目标 display 的 `smallestScreenWidthDp`、应用类别与设备设置。

大屏上的形态约束减少后，`android:configChanges` 的风险也跟着变化。应用仍可声明自行处理某些配置变化，但窗口被拉伸、旋转或进入分屏、桌面窗口时，Activity 更容易连续收到尺寸、方向、screen layout 变化。声明了 `configChanges` 的应用同样要更新资源、布局和渲染目标；声明缺失时，系统仍可能重建 Activity。

API 37 的 `recreateOnConfigChanges` 针对的是另一类变化，与大屏形态规则无关：它面向 touchscreen、keyboard、keyboardHidden、navigation、colorMode，用来恢复这些变化触发 Activity 重建的旧行为，`screenOrientation`、宽高比和 resizability（可调整大小）限制不会因它重新生效。对渲染分析来说，大屏和外接显示器上的窗口尺寸变化会更频繁地触发 relayout、buffer 重新分配和 `performTraversals()`；应用应保存 UI state，把窗口尺寸变化当作常态输入。

## Multi-resume 下的焦点与可见性

多窗口里，失去焦点离进入 `onStop()` 还很远。Android 10（API 29）引入 Multi-resume（多 Activity 同时恢复）后，多个可见 Activity 可以同时停留在 `RESUMED`；画中画等不具备焦点的窗口可能进入暂停状态，但只要 Activity 仍在屏幕上，我们就要按可见窗口对待它的生命周期，而不是按已停止的后台窗口推导。

**顶层恢复（top resumed）** 是资源仲裁和交互强度调整的重要信号，但它没有规定失去顶层就必须释放相机：官方允许非 top-resumed 的可见 Activity 继续相机预览，应用仍要处理 `CameraDevice.StateCallback#onDisconnected()` 等资源抢占信号。高频动画、连续 invalidation（请求重绘）和 frame-rate vote，要同时参考 top-resumed、实际可见性与内容是否仍在更新。

下面的代码分别处理顶层交互资格变化和 Activity 进入 `onStop()` 后的离屏状态：

```kotlin
override fun onTopResumedActivityChanged(topResumed: Boolean) {
    super.onTopResumedActivityChanged(topResumed)
    if (topResumed) {
        resumeHighFrequencyRendering()
        tryReacquireExclusiveResources()
    } else {
        dropNonEssentialAnimations()
        prepareForExclusiveResourcePreemption()
    }
}

override fun onStop() {
    super.onStop()
    stopOffscreenWork()
}
```

三个分支的处理范围不同：

- `topResumed = true`：窗口取得前台交互资格，可以尝试获取独占资源并恢复高交互频率。
- visible 但非 top resumed，窗口可能仍处于 `RESUMED`。视频小窗、导航小窗和分屏副窗口都可能属于这一类。此时适合减少非必要重绘、准备处理资源抢占，全部停掉渲染不可取。
- `onStop()`：只在 Activity 离开屏幕时触发，离屏工作在这里停止。

PiP 也要单独判断：它通常“可见但拿不到输入焦点”。持续播放视频时，要按动态窗口对待；内容已暂停时，则无须每帧都做完整 UI 刷新。

## 优化策略

优化要对准已经确认的责任阶段。“减少 Window 数”只解决一部分共享线程或合成开销，替代不了对迟到阶段的定位。

### 同 UI Looper

- 停止被遮挡窗口中不必要的动画、定时刷新和持续 invalidate；
- 缩小实际需要更新的 View 子树，避免无关 `requestLayout()`；
- 把非 UI 计算移出主线程，同时保留 View 访问的线程约束；
- Dialog/Popup 首帧提前准备数据、图片与布局输入，避免 show 时同步 I/O；
- 浮层若不需要独立 Window 提供焦点、Insets、安全策略或系统行为，可以评估放进现有 View hierarchy。

把 Dialog 改成宿主窗口内的 overlay（覆盖层），会少一个 ViewRoot/Surface，但宿主的重绘范围可能变大，输入、Insets、无障碍和生命周期行为也会改变。要不要这么做，要在目标场景里验证，窗口数量只是其中一个变量。

### 共享 RenderThread / GPU

- 找出长期占用队列的具体 CanvasContext、dequeue/fence wait 或 GPU pass；
- 减少背景 Window 的无效 draw、全屏模糊、大面积透明和离屏 layer；
- 检查各窗口的 buffer 尺寸是否随 bounds 调整，避免小窗长期生产全尺寸内容；
- 按实际使用的 SkiaGL/SkiaVulkan backend 分析，EGL 的固定结论直接套用会有偏差。

### resize、PiP 与 transition

- 正确处理 configuration、window bounds、Insets 和状态保存；
- 避免在 resize loop（连续尺寸变化的回调周期）中反复分配大 Bitmap/buffer 或重建重量级资源；
- 让 geometry transaction 与新尺寸 buffer 进入既定的 sync/transition 边界；
- 记录 starting window、snapshot 和 letterbox 的预期策略，避免把过渡期的旧 buffer 缩放误判成应用黑屏。

### 跨进程与 HWC

- 分别修复每个 App 的 late frame，一个进程的 slice 顶替不了另一个进程的观察结果；
- 比较问题前后的 visible layer set、DEVICE/CLIENT、client target 和 display mode；
- 分析 protected、HDR 或外接屏问题时，结合目标设备能力和 vendor trace；
- 低帧率 PiP 按媒体内容的供帧节奏判断，无须要求每次 Display VSync 都产生新 buffer。

## 版本演进

| Android 版本 | 公开变化 | 对渲染分析的影响 |
|---|---|---|
| 7.0 (API 24) | 引入 split-screen，freeform capability（自由窗口能力）进入平台 | SurfaceFlinger 开始稳定处理多个可见应用窗口 |
| 8.0 (API 26) | PiP 扩展到小屏设备 | 主窗口之外增加一条持续更新的小窗 layer |
| 10 (API 29) | Multi-resume 与 `onTopResumedActivityChanged()` | 失去焦点不再等于离开 `RESUMED`，生命周期判断需要细分 |
| 12 (API 31) | 多窗口成为大屏设备的标准行为 | 平板、折叠屏更频繁进入 resizable/compatibility mode |
| 12L (API 32) | 大屏系统 UI、多任务与 Activity Embedding（Activity 嵌入）体验增强 | 同一 Task window 可包含并列的 Activity container，视觉双栏仍可能只有一个顶层 Window |
| 13 (API 33) | Composer HAL 转向 AIDL；AutoSingleLayer 仅覆盖受限的单 layer buffer update | HAL 接口变化不改变 per-display（逐显示）HWC 职责；不能用 unsignaled latch（未发信号时锁存）解释跨窗口同步 |
| 14 (API 34) | `SurfaceSyncGroup` 成为公开 API | 应用和嵌入 Surface 可收集同步 transaction，WMS 内部仍使用独立 sync engine |
| 15 (API 35) | target 35 edge-to-edge（内容延伸到系统栏区域）；`PROPERTY_SUPPORTS_MULTI_INSTANCE_SYSTEM_UI` 提供多实例声明 | caption、Insets 和多实例窗口增加布局与任务组织变量，不改变 BLAST/SF 主线 |
| 16 (API 36) | target 36 在 `sw >= 600dp` 时忽略方向、宽高比和 resizability 限制，并提供临时 opt-out（退出选项） | 窗口尺寸与方向变化更常见；测试要覆盖 desktop window、外屏、折叠状态和 compatibility mode |
| 17 (API 37) | target 37 不再支持上述 opt-out；`recreateOnConfigChanges` 扩展到新的默认不重建配置类型；target 37 启用 lock-free MessageQueue | 大屏适配不能依赖固定方向或不可缩放；DeliQueue 的收益仅限 Looper 队列，显示主线仍按 Android 17 AOSP 分析 |

## 常见问题与误区

### 误区 1：失去焦点与 `onStop()` 的关系

Android 10 之后，多窗口中的多个可见 Activity 可以同时停留在 `RESUMED`。焦点、可见性、top resumed 是三套不同的信号，资源与渲染策略要分别处理。

### 误区 2：`recreateOnConfigChanges` 与窗口尺寸变化

这个属性只声明哪些默认不重建的配置变化仍要触发重建。折叠屏展开、窗口缩放、横竖屏切换，仍要检查 `android:configChanges`、`onConfigurationChanged()`、状态保存，以及系统是否触发 Activity 重建。API 37 对 touchscreen、keyboard、keyboardHidden、navigation、colorMode 的处理，外推不到窗口尺寸变化上。

### 误区 3：多窗口掉帧的归因顺序

多窗口也会增加 Shell transaction、SurfaceFlinger output 和 HWC 策略变量。先查 FrameTimeline 的 `jank_type`，再看目标 output 的 layer 快照与 composition type；确认最早发生延迟的阶段后，修复对象属于应用、系统还是设备就清楚了。

### 误区 4：GPU composition 的触发条件

HWC 评估的是整个 output 的 layer 属性和硬件资源。多个简单 layer 仍可能全部采用 DEVICE 合成，单个带复杂变换、HDR 混合或受保护内容的窗口也可能改变策略。

### 误区 5：layer snapshot 与 display 的关联

`surfaceflinger_layer` 没有 `display_id`。多 display trace 要先确认 Winscope output，再结合 transaction、layer parent 和目标时间片做归属；把 snapshot 中的所有 layer 整包算到每块屏幕，是常见的误归属。

## 参考资料

- [AOSP `DisplayManagerService`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/DisplayManagerService.java)
- [AOSP `LogicalDisplayMapper`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/LogicalDisplayMapper.java)
- [AOSP `LogicalDisplay`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/LogicalDisplay.java)
- [AOSP `LocalDisplayAdapter`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/LocalDisplayAdapter.java)
- [AOSP `ExternalDisplayPolicy`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/display/ExternalDisplayPolicy.java)
- [AOSP `ViewRootImpl`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/ViewRootImpl.java)
- [AOSP `Choreographer`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)
- [AOSP HWUI `RenderThread`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/RenderThread.cpp)
- [AOSP manifest `recreateOnConfigChanges`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/res/res/values/attrs_manifest.xml)
- [AOSP `WindowContainerTransaction`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/window/WindowContainerTransaction.java)
- [AOSP `SurfaceSyncGroup`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/window/SurfaceSyncGroup.java)
- [AOSP `WindowContainer`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/WindowContainer.java)
- [AOSP `BLASTSyncEngine`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/BLASTSyncEngine.java)
- [AOSP `BLASTBufferQueue`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BLASTBufferQueue.cpp)
- [AOSP `SurfaceFlinger`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)
- [AOSP `HWComposer`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/DisplayHardware/HWComposer.cpp)
- [Android Developers：Multi-window mode](https://developer.android.com/develop/ui/compose/layouts/adaptive/support-multi-window-mode)
- [Android Developers：Desktop windowing](https://developer.android.com/develop/ui/compose/layouts/adaptive/support-desktop-windowing)
- [Android Developers：Connected displays](https://developer.android.com/develop/ui/compose/layouts/adaptive/support-connected-displays)
- [Android Developers：Picture-in-picture](https://developer.android.com/develop/ui/views/picture-in-picture)
- [AOSP：Multi-window support](https://source.android.com/docs/core/display/multi-window)
- [AOSP `PictureInPictureParams`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/PictureInPictureParams.java)
- [AOSP `PipTaskOrganizer`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/pip/PipTaskOrganizer.java)
- [Android Developers：Android 16 behavior changes](https://developer.android.com/about/versions/16/behavior-changes-16)
- [Android Developers：Android 17 behavior changes](https://developer.android.com/about/versions/17/behavior-changes-17)
- [Android Developers Blog：Android 17 lock-free MessageQueue](https://android-developers.googleblog.com/2026/02/under-hood-android-17s-lock-free.html)
- [PerfettoSQL standard library](https://perfetto.dev/docs/analysis/stdlib-docs)
- [Perfetto FrameTimeline](https://perfetto.dev/docs/data-sources/frametimeline)
- [AOSP Graphics：SurfaceFlinger and WindowManager](https://source.android.com/docs/core/graphics/surfaceflinger-windowmanager)
- [AOSP Graphics：Hardware Composer HAL](https://source.android.com/docs/core/graphics/hwc)
- [`android17-6.18-2026-06_r6`：sync_file](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)
- [`android17-6.18-2026-06_r6`：dma-fence](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c)
