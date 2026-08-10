---
title: "TaskSnapshot 捕获、Overview 缩略图与启动窗口"
chapter: "2.29"
status: ready-for-review
drafted_date: "2026-06-24"
applicable_versions: "Android 8 (API 26) - Android 17 (API 37)"
last_verified: "2026-07-25"
last_verified_against: "AOSP android-17.0.0_r1 + Launcher3 android-17.0.0_r1"
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/perf/task-snapshots"
  - type: official
    path: "https://developer.android.com/reference/android/app/Activity#setRecentsScreenshotEnabled(boolean)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/SnapshotController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/AbsAppSnapshotController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/SnapshotPersistQueue.java"
  - type: aosp
    path: "frameworks/base/core/java/android/window/SnapshotDrawerUtils.java"
  - type: aosp
    path: "frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/"
  - type: aosp
    path: "packages/apps/Launcher3/quickstep/src/com/android/quickstep/"
tags: [tasksnapshot, recents, overview, rendering, memory, surfaceflinger]
related_chapters: ["2.6", "2.12", "2.13", "2.15", "4.1", "8.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "AOSP结构+章节深挖"
gap_score: 14
---

# 2.29 TaskSnapshot 捕获、Overview 缩略图与启动窗口

TaskSnapshot 从 Android 8.0 开始统一了两类历史能力：最近任务缩略图和 WindowManager 保存的 Surface。到了 Android 17，同一份 `TaskSnapshot` 仍可用于多个场景，但各场景的显示对象并不相同。

先区分四个容易混用的概念：

| 概念 | 内容来源 | 显示位置 | Android 17 的主要对象 |
|---|---|---|---|
| TaskSnapshot | WMS 请求捕获任务 Surface 子树 | 缓存、磁盘或跨进程传递 | `android.window.TaskSnapshot` |
| Overview 静态缩略图 | TaskSnapshot 包装成硬件 `Bitmap` | Launcher/Quickstep 自己的窗口 | `ThumbnailData`、`TaskThumbnailView` |
| Overview live tile | 正在参与 Recents animation 的真实 Task surface | remote animation leash | `RemoteAnimationTarget`、leash |
| snapshot starting window | 旧 TaskSnapshot 作为启动占位 | 独立 starting-window surface | `TaskSnapshotWindow` |

这四者的缓冲区、SurfaceControl、生命周期和性能瓶颈不同。看到 Overview 卡片时，不能直接推导屏幕上存在一个名为 TaskSnapshot 的独立 SurfaceFlinger layer。

以下分析以 Android 17 / API 37 / `android-17.0.0_r1` 为准，Launcher 侧同时参考 `packages/apps/Launcher3` 的同名标签。Android 8～16 仅用于说明版本演进。

## 1. TaskSnapshot 保存了什么

### 1.1 HardwareBuffer 只是对象的一部分

Android 17 的 `TaskSnapshot` 包含：

- 捕获结果 `HardwareBuffer`；
- `ColorSpace`；
- top Activity component；
- 屏幕方向与显示旋转；
- 原始 task size；
- content insets 与 letterbox insets；
- high/low resolution 标记；
- 真实快照或应用主题快照标记；
- windowing mode、system-bar appearance、translucency；
- 是否包含 IME surface；
- density DPI；
- snapshot id 与 capture time。

这些元数据决定消费端如何旋转、裁剪、缩放和判断兼容性。只保存一张 PNG 或 JPEG，无法复现 Android 17 的启动窗口与 Overview 行为。

`HardwareBuffer` 通过 Binder 传递的是底层缓冲区句柄和引用，不需要把整张像素图复制进 Parcel。接收方仍要管理引用、等待可用状态并参与后续 GPU/HWC 合成；跨进程零像素复制仍有处理成本。

### 1.2 TaskSnapshot 与 LayerSnapshot 名字相近，职责不同

Android 17 的 SurfaceFlinger FrontEnd 使用 `LayerSnapshot` 描述当前帧的图层可见性、几何、Z-order、缓冲区与效果状态。WMS 的 `TaskSnapshot` 是对一个任务 Surface 子树执行屏幕捕获后生成的可复用图像。

两者关系如下：

```text
SF LayerSnapshot 集合
  → screen capture 合成
    → 新的截图 HardwareBuffer
      → WMS TaskSnapshot
```

因此，Perfetto 或源码里出现 `LayerSnapshotBuilder`，不代表系统正在生成最近任务缩略图。它也可能只是 SurfaceFlinger 为普通显示帧更新 FrontEnd 状态。

## 2. Android 17 的捕获时机

### 2.1 Shell 过渡在事务就绪阶段记录

现代过渡路径由 `SnapshotController.onTransactionReady()` 检查 `Transition.ChangeInfo`。对于满足条件且将不可见的任务，系统会在过渡事务启动前调用：

```text
SnapshotController.onTransactionReady()
  → TaskSnapshotController.recordSnapshot(task, changeInfo)
    → AbsAppSnapshotController.recordSnapshotInner()
```

Android 17 会排除或特殊处理：

- 桌面与画中画变化；
- 由组织器创建的任务；
- transient hide；
- Task 仍为 `isVisibleRequested()`；
- 某些显示变化同时改变边界的场景。

传入 `ChangeInfo` 是因为任务配置可能已在过渡准备阶段改变。捕获时仍要使用关闭前的旋转和边界，避免把旧画面配上新几何。

### 2.2 休眠前还有一条捕获路径

屏幕即将关闭或设备进入休眠时，`snapshotForSleeping(displayId)` 会遍历对应显示器上的可见叶任务。正在由最近任务动画控制的任务会被跳过，因为最近任务路径需要在更合适的时刻处理快照和 IME。

安全锁屏进入休眠时，默认显示器的桌面任务也可能被捕获，用于解锁返回桌面时的启动窗口。

### 2.3 特权调用方可以主动请求

Android 17 的隐藏系统 API `TaskSnapshotManager.takeTaskSnapshot()` 允许具备系统权限的调用方对仍可见的 Task 请求新快照。`SnapshotManagerService` 会验证 Task 存在且可见，再决定是否更新系统缓存。

Launcher3 在缩略图缺失时会先读取已有快照，仍为空时再请求 `takeTaskThumbnail()`。普通第三方应用没有这组任务管理与帧缓冲区读取权限。

### 2.4 没有通用的冻结前快照钩子

Android 17 的 `TaskSnapshotController` 没有“每次冻结前先截取任务”的通用入口。快照主要围绕过渡、休眠和特权主动请求生成。

同理，源码没有向应用承诺：

```text
capture snapshot → onPause() → transition start
```

WMS visibility、ATMS lifecycle transaction、Shell transition 和应用主线程分别调度。应用不应依赖 snapshot 与 `onPause()` 的固定先后；系统只尽量在 Task 关闭前保留可用于过渡的视觉状态。

## 3. 捕获管线与安全边界

### 3.1 真实画面的调用链

Android 17 捕获真实快照的主线是：

```mermaid
flowchart TD
    A["SnapshotController 选择目标 Task"] --> B["TaskSnapshotController.recordSnapshot"]
    B --> C["AbsAppSnapshotController.prepareTaskSnapshot"]
    C --> D["ScreenCaptureInternal.captureLayersExcluding"]
    D --> E["SurfaceFlinger captureLayersSync"]
    E --> F["captureScreenCommon / renderScreenImpl"]
    F --> G["Screenshot HardwareBuffer + ColorSpace"]
    G --> H["TaskSnapshot"]
    H --> I["system_server cache"]
    H --> J["SnapshotPersistQueue"]
    H --> K["TaskSnapshot listener / Binder consumer"]
```

`captureLayersExcluding()` 捕获的是 Task `SurfaceControl` 子树。Android 17 会按状态排除：

- 不应附着到应用的 IME Surface；
- navigation bar surface；
- 正在退出且不属于基础应用的部分窗口；
- 任务明确登记在 `mExcludeLayersFromTaskSnapshot` 中的图层。

捕获会生成新的截图缓冲区，而非直接读取某个应用窗口最近提交的 `GraphicBuffer`。任务中可能包含多个窗口、SurfaceView、壁纸或装饰图层，SurfaceFlinger 要根据当前图层状态生成捕获结果。

### 3.2 同步捕获会进入 transition 关键路径

`ScreenCaptureInternal.captureLayers()` 在这条路径中调用原生同步捕获，并等待 `ScreenshotHardwareBuffer` 结果。SurfaceFlinger 的 `captureLayersSync()` 最终经过 `captureScreenCommon()` 与截图渲染。

高分辨率、复杂图层树、GPU 繁忙或缓冲区分配压力可能延长 WMS 和过渡的准备时间。不能只看应用的 `doFrame()` 判断进入 Overview 时的卡顿。

AOSP 没有给出“1080p 必须耗时 5～15 ms”一类保证。截图策略、SoC、RenderEngine、图层数量、像素格式和系统负载都会改变结果，应从目标设备的跟踪记录取值。

### 3.3 REAL、APP_THEME 与 NONE

`AbsAppSnapshotController.getSnapshotMode()` 会选择：

- `SNAPSHOT_MODE_REAL`：捕获真实 Task 内容；
- `SNAPSHOT_MODE_APP_THEME`：根据 `TaskDescription` 和窗口背景生成主题占位；
- `SNAPSHOT_MODE_NONE`：不生成任务快照。

Recents activity 和 dream activity 不捕获 Task snapshot。TV、IoT 或设备 overlay `config_disableTaskSnapshots=true` 也可以关闭该能力。

以下情况会选择应用主题快照：

- Activity 调用 `setRecentsScreenshotEnabled(false)`；
- 任务中的窗口被 `FLAG_SECURE`、敏感内容策略或设备策略判定为安全窗口。

主题占位由 system_server 使用 `RenderNode` 和 `ThreadedRenderer.createHardwareBitmap()` 绘制，包含背景色与系统栏装饰信息，不含应用的敏感像素。

### 3.4 两个隐私 API 的范围不同

`Activity.setRecentsScreenshotEnabled(false)` 从 API 33 开始公开，只禁止 Activity 的画面被用作 Overview 表示。系统仍可能在其他允许的场景截图。

`FLAG_SECURE` 的范围更广：它阻止窗口进入普通截图，并限制在非安全显示器上显示。处理登录、支付或隐私数据时，应按威胁模型选择，不能把 Overview 开关当成 `FLAG_SECURE` 的替代品。

## 4. 内存缓存、磁盘文件与分辨率

### 4.1 system_server 缓存不是 LRU

Android 17 的 `SnapshotCache` 使用：

```text
ArrayMap<Integer, CacheEntry> mRunningCache
```

key 是 task id。它没有按访问顺序淘汰的 LRU 逻辑。常见清理时机包括：

- top Activity removed 或进程死亡；
- Task 从 Recents 删除；
- Task 重新变为可见并完成 transition；
- 系统显式清空快照缓存。

进程死亡时，system_server 的运行时缓存项会删除；已经持久化的磁盘文件可以继续用于后续 Overview 或启动恢复。Launcher 进程还维护独立的缩略图缓存。

Android 17 还包含由 `onlyCacheLowResTaskSnapshot` 功能开关控制的路径：高分辨率快照可在转换完成后由低分辨率版本替换，旧高分辨率缓冲区最多短暂保留 5 秒以处理并发请求。这是开关控制的内存策略，不能视为所有 Android 17 设备的固定行为。

### 4.2 内存估算要包含缩放、格式与行跨度

单个未压缩缓冲区的下限估算为：

```text
width × height × bytesPerPixel
```

例如，1080×2400 的 RGBA_8888 可见像素约为 9.9 MiB。实际分配还受行跨度、gralloc 对齐和附加元数据影响；同时存在高低分辨率版本、Binder 引用、Launcher hardware `Bitmap` 或启动窗口引用时，总占用会进一步变化。

默认情况下，真实快照使用 RGBA_8888。设备资源覆盖项开启 `config_use16BitTaskSnapshotPixelFormat` 后，填满父窗口且不会因透明窗口与壁纸丢失透明度的任务可以使用 RGB_565。

因此，“低内存设备一定缓存 3～5 张、一定使用 RGB_565”没有 Android 17 源码依据。厂商可通过以下资源覆盖项调整：

- `config_highResTaskSnapshotScale`；
- `config_lowResTaskSnapshotScale`；
- `config_use16BitTaskSnapshotPixelFormat`；
- `config_disableTaskSnapshots`。

AOSP 默认高分辨率缩放系数为 1.0，低分辨率缩放系数为 0.5；将低分辨率缩放系数设为 0 可以关闭缩略快照。

### 4.3 持久化在线程队列完成

`SnapshotPersistQueue` 使用名为 `TaskSnapshotPersister` 的后台线程。一次 store 会：

1. 写入快照元数据的 proto 文件；
2. 把 HardwareBuffer 复制成软件 `Bitmap`；
3. 写入高分辨率图像；
4. 配置允许时生成并写入低分辨率图像。

Android 17 的压缩质量常量为 95。文件位于用户 CE system 目录下：

```text
/data/system_ce/<userId>/snapshots/<randomized-directory>/
```

典型文件名为：

```text
<taskId>.proto
<taskId>.jpg
<taskId>_reduced.jpg
```

部分功能开关路径会用 PNG 编码高分辨率内容，但仍沿用 `.jpg` 文件名。排查文件格式时应读取文件头，不能只看后缀。

队列会合并同一任务、用户和提供器的重复写入，并限制待处理的 HardwareBuffer 存储项数量，避免后台持久化积压无限占用图形内存。

### 4.4 从磁盘恢复包含解码和重新上传

`AppSnapshotLoader` 先读取 proto 文件，再用 `BitmapFactory.decodeFile()` 解码图像，随后复制为 `Config.HARDWARE` 位图并取得 `HardwareBuffer`。

磁盘恢复与内存命中差别很大：

| 路径 | 主要工作 |
|---|---|
| system_server 内存命中 | 引用管理与 Binder 传递 |
| 磁盘高低分辨率图像加载 | 文件 I/O、图像解码、硬件位图分配 |
| Launcher 本地缓存命中 | 直接复用 `ThumbnailData` |

没有跟踪记录时，不能把 Overview 空卡统一归因于 GPU；耗时也可能出现在磁盘、Binder、Launcher 执行器或主线程数据绑定。

## 5. Overview：静态缩略图与 live tile

### 5.1 静态缩略图由 Launcher 自己绘制

Launcher3 的主要读取路径是：

```text
TaskThumbnailCache
  → ActivityManagerWrapper.getTaskThumbnail()
    → TaskSnapshotManager.getTaskSnapshot()
      → SnapshotManagerService
        → 系统缓存或磁盘
```

收到 `TaskSnapshot` 后，`ThumbnailData.fromSnapshot()` 调用 `wrapToBitmap()`，把 HardwareBuffer 包装为硬件 `Bitmap`，同时保存旋转、Insets、缩放系数和窗口模式等信息。

Android 17 Launcher3 的 `TaskThumbnailView` 是 Launcher View 层级中的 `FrameLayout`。静态快照最终设置到 `FixedSizeImageView`，由 Launcher 的 View/HWUI 管线绘制进 Launcher App Window buffer。

SurfaceFlinger 看到的主体通常是 Launcher 窗口图层，而非每张最近任务卡片各有一个独立 BufferStateLayer。HWC 仍会根据整屏图层集合选择设备合成或客户端合成；hardware `Bitmap` 不保证卡片获得独立的硬件叠加层。

### 5.2 Launcher 还有自己的缓存和预加载

`TaskThumbnailCache` 的容量来自 Launcher 资源 `recentsThumbnailCacheSize`，与 system_server `SnapshotCache` 无关。它支持：

- 低分辨率、高分辨率或任意分辨率请求；
- 后台执行器加载；
- 缓存容量变化后的裁剪；
- 进入 Overview 前预加载；
- `onTaskSnapshotChanged` 后更新已有缓存项；
- `TRIM_MEMORY_RUNNING_CRITICAL` 时清空缩略图与图标缓存。

排查内存时至少要区分 system_server 的 TaskSnapshot buffer、Launcher 的 hardware `Bitmap` 引用和屏幕上 Launcher App Window buffer。

### 5.3 实时卡片使用真实任务牵引层

Quickstep 的 `TaskUiStateMapper` 会为当前运行中的任务且允许实时显示的场景选择 `LiveTile`。最近任务动画把真实任务作为 `RemoteAnimationTarget` 交给 Launcher，Launcher 通过事务为牵引层设置几何变换、裁剪和透明度。

实时卡片与静态缩略图的选择不能简化为：

```text
进程存活 → live tile
进程冻结或死亡 → snapshot
```

一个仍存活的后台任务可以显示静态快照；实时卡片通常对应当前正在参与最近任务动画的运行中任务。是否显示截图还受手势状态、锁定状态、最小化状态和 Launcher 实现影响。

### 5.4 点击卡片有两类启动路径

点击当前运行中的实时卡片时，Quickstep 可以沿远程目标牵引层执行返回应用的动画。

点击静态卡片时，Launcher 发起 `startActivityFromRecents()`。随后 WMS 可能：

- 直接等待已有应用窗口；
- 创建快照启动窗口；
- 因快照不兼容而改用启动画面；
- 在 Task/Activity 已满足显示条件时不创建启动窗口。

因此，Android 17 不能统一描述为“Launcher 把静态快照图层渐变切换为应用实时 Surface”。Launcher 静态缩略图、Shell 远程牵引层和 WMS 启动窗口是三套不同对象。

## 6. Snapshot starting window

### 6.1 WMS 先判断能否使用旧快照

`ActivityRecord.getStartingWindowType()` 会结合任务切换、进程与 Activity 状态、是否允许快照等条件选择启动窗口类型。

使用快照前还要检查：

- top Activity component 是否兼容；
- 快照旋转是否等于目标旋转；
- 快照任务宽高比与当前边界的差值是否在源码阈值内。

Android 17 对宽高比使用 0.01 的绝对差阈值。折叠、旋转或桌面窗口缩放后旧快照不兼容时，系统通常回退到启动画面或不显示该快照。

### 6.2 Shell 创建独立 starting surface

快照启动窗口的主线是：

```mermaid
flowchart TD
    A["ActivityRecord 选择快照启动类型"] --> B["StartingWindowInfo + TaskSnapshot"]
    B --> C["Shell StartingWindowController"]
    C --> D["StartingSurfaceDrawer"]
    D --> E["TaskSnapshotWindow"]
    E --> F["SnapshotDrawerUtils.drawSnapshotOnSurface"]
    F --> G["SurfaceControl.Transaction.setBuffer / setColorSpace"]
    G --> H["SurfaceFlinger 合成启动窗口图层"]
```

这里的快照是独立的 SurfaceControl 缓冲区图层，与 Launcher 静态卡片的 ImageView 路径不同。App BLAST 生产者提交。

### 6.3 尺寸不一致时会缩放

`SnapshotDrawerUtils` 比较快照缓冲区与目标窗口边界。尺寸相同且没有信箱偏移时，缓冲区可直接设置到根 Surface。

尺寸不一致时，系统会：

- 创建或使用匹配缓冲区的 BLAST Surface；
- 按信箱 Insets 调整位置；
- 分别计算 X/Y 缩放系数以填充目标边框；
- 设置快照色彩空间；
- 提交缓冲区事务。

这条路径能遮住部分窗口缩放间隙，但也可能让旧内容短暂缩放。它不能修复应用的新布局；应用仍要提交符合新边界的首帧。

### 6.4 移除时机与 IME

应用内容就绪后，TaskOrganizer 请求移除启动窗口。普通快照可以立即或延迟移除；包含 IME 的快照还会等待新的 IME 绘制回调或超时。

Android 17 的 Shell 代码包含 100 ms、600 ms 和 3000 ms 三种延迟上限，分别用于一般延迟、IME 和固定旋转情况。它们是特定移除模式的保护值，不代表所有应用冷启动都会固定等待这些时间。

## 7. 折叠屏、多窗口与多显示器

### 7.1 Overview 会按元数据调整缩略图

Launcher3 的 `PreviewPositionHelper` 使用：

- snapshot rotation；
- `ThumbnailData.scale`；
- letterbox insets；
- 快照与卡片的宽高比；
- 当前设备密度；
- 分屏边界与分区位置；
- RTL 与大屏布局状态。

它为 ImageView matrix，对静态缩略图执行旋转、裁剪和缩放。折叠后卡片显示正常，只能说明 Launcher 的缩略图适配成功，不能证明 WMS 启动窗口或应用首帧也匹配。

### 7.2 启动窗口的兼容检查更严格

折叠前后的任务边界可能在旋转不变时改变宽高比。`ActivityRecord.isSnapshotOrientationCompatible()` 会比较快照的 `taskSize` 与当前任务边界；差异超过阈值时不使用快照启动窗口。

Android 17 不会在每次显示变化时重新捕获所有任务；当前 `TaskSnapshotController` 没有通用的 `handleDisplayChange()` 或 `snapshotBeforeDisplayChange()` 路径。

### 7.3 一个任务归属一个 DisplayContent

AOSP WindowManager 中，一个任务在某一时刻归属于一个 DisplayContent。任务可以在显示器之间移动，桌面 Overview 也可以组合展示多个任务，但不存在一个普通任务同时跨两个 DisplayContent 捕获主、副区域的通用模型。

捕获入口使用该任务自己的 `SurfaceControl` 与所在显示器的状态。排查多显示器问题时要记录：

- task id 与 display id；
- 捕获时的 task bounds、rotation、density、windowing mode；
- 用于显示 Overview 的显示器；
- 启动窗口与应用窗口最终出现在哪个显示器。

## 8. 颜色、透明度与 HWC

### 8.1 ColorSpace 会随 TaskSnapshot 传递

SurfaceFlinger 捕获结果返回 `HardwareBuffer` 和 `ColorSpace`。TaskSnapshot 透传这两项：

- Launcher 把缓冲区包装为硬件 `Bitmap`；
- 启动窗口通过 `SurfaceControl.Transaction.setColorSpace()` 标记 Surface。

不能假设广色域任务一定得到 `DISPLAY_P3`；最终数据空间由捕获内容、Display color mode、HDR/SDR 策略和 SurfaceFlinger 截图路径共同决定。

### 8.2 透明快照需要背景

真实快照的像素格式可以是 RGBA_8888，`TaskSnapshot.isTranslucent()` 记录任务是否可能透出背景。Launcher3 会先绘制 TaskDescription background，再显示缩略图，避免透明或局部为空的快照露出错误内容。

快照启动窗口同样从 `TaskDescription` 取背景色，并处理系统栏区域。只看截图缓冲区，可能漏掉最终屏幕上的背景和装饰。

### 8.3 HardwareBuffer 不决定合成类型

TaskSnapshot 使用 gralloc buffer，可被 GPU 采样，也可在满足设备约束时参与 HWC DEVICE composition。最终选择取决于：

- layer transform、crop、alpha 与圆角；
- 目标显示器与数据空间；
- overlay 数量和格式支持；
- 其他可见图层；
- protected/secure 内容；
- HWC validate 结果。

Overview 静态卡片通常已经画入 Launcher App Window；启动快照更可能表现为独立图层。两者不能共用“HWC 直接合成快照”这一结论。

## 9. 性能观测

### 9.1 先确定测量对象

建议分别定义：

| 问题 | 起点 | 终点 |
|---|---|---|
| 后台切换卡顿 | 过渡收集或就绪 | 快照捕获返回或过渡事务生效 |
| Overview 空卡 | Launcher 发起缩略图请求 | `TaskThumbnailView` 所在的 Launcher 帧送显 |
| 点击最近任务闪烁 | 卡片点击或启动过渡 | 应用新缓冲区在目标显示器送显 |
| starting window 停留过久 | `TaskSnapshot#addToDisplay` | snapshot starting surface remove + App frame present |
| 缩略图过旧 | snapshot capture time/id | 用户打开 Overview 的时间 |

捕获耗时、磁盘恢复耗时和显示耗时是三段数据，不能只报告一个“TaskSnapshot latency”。

### 9.2 Perfetto 关注的 Android 17 slice

建议采集调度、Binder、图形、View 与 WindowManager：

```bash
adb shell perfetto \
  -o /data/misc/perfetto-traces/task-snapshot.perfetto-trace \
  -t 15s \
  sched freq idle binder_driver gfx view wm
```

Android 17 中可搜索：

- `createSnapshot`；
- `captureLayers`、`captureScreenCommon`、`captureScreenshot`、`renderScreenImpl`；
- `StoreWriteQueueItem#<taskId>`；
- `getTaskSnapshot#<taskId>_res=...`；
- `getSnapshotFromDisk_Id=...`；
- `createLowResSnapshot`、`waitSnapshotUpdated_Id=...`；
- `TaskSnapshot#addToDisplay`、`TaskSnapshot#relayout`、`TaskSnapshot#relayoutAsync2`；
- Launcher thumbnail executor、View traversal、HWUI 与 FrameTimeline；
- 最近任务动画的远程目标牵引层事务；
- 应用首帧的 `BufferTX`、锁存事件与目标显示器送显。

一个简单的 Trace Processor 查询可以先列出相关切片：

```sql
SELECT
  name,
  ts / 1e6 AS ts_ms,
  dur / 1e6 AS dur_ms
FROM slice
WHERE name GLOB '*Snapshot*'
   OR name IN (
     'createSnapshot',
     'captureLayers',
     'captureScreenCommon',
     'captureScreenshot',
     'renderScreenImpl'
   )
ORDER BY ts;
```

这条查询只用于查找候选区间。随后还要按进程、线程、流和目标任务或显示器对齐，避免把普通截图或 SurfaceFlinger 的 `LayerSnapshot` 更新算入 TaskSnapshot。

### 9.3 dumpsys 与文件检查

以下命令用于建立静态快照：

```bash
adb shell dumpsys window | grep -A 40 -i SnapshotCache
adb shell dumpsys activity recents
adb shell dumpsys SurfaceFlinger --list | grep -i -E 'snapshot|starting|recents'
adb shell dumpsys meminfo <launcher-package>
```

注意：

- cached TaskSnapshot 没有显示到屏幕时，不一定出现在 SF layer list；
- `SurfaceFlinger --list` 中的快照图层更可能是启动窗口；
- system_server 与 Launcher 持有同一底层缓冲区的引用时，按进程简单相加可能重复计算共享 DMA-BUF；
- `/data/system_ce` 文件检查通常需要 root/userdebug 权限。

支持的调试构建还可以用 DMA-BUF 统计工具确认导出方、inode、size Java 堆判断 TaskSnapshot 图形内存。

## 10. 常见故障的定位顺序

### 10.1 进入 Overview 时掉帧

依次检查：

1. 过渡就绪前是否出现耗时较长的 `createSnapshot`；
2. SF 捕获耗时出现在图层收集、缓冲区分配还是 RenderEngine；
3. Launcher 是否同步等待磁盘快照；
4. 是否先显示低分辨率图像，以及高分辨率更新是否造成额外绑定；
5. Launcher 主线程、RenderThread 和最终 DisplayFrame 是否按时。

### 10.2 卡片显示黑色或主题色

检查 `ThumbnailData.isRealSnapshot`、Activity 的最近任务截图开关、`FLAG_SECURE`、设备策略和应用锁状态。主题色卡片可能是预期的应用主题快照，不代表捕获失败。

### 10.3 卡片旧，但应用已更新

记录快照 snapshot id/capture time，并确认任务最近一次转为不可见的时间。后台仍存活不代表系统会持续刷新静态缩略图；实时卡片也只覆盖正在参与最近任务动画的目标。

### 10.4 点击卡片后画面跳变

区分三张画面：

1. Launcher 静态缩略图；
2. WMS/Shell snapshot starting window；
3. 应用新提交的窗口缓冲区。

比较三者的 task bounds、rotation、density、contentInsets、letterboxInsets 和首帧内容。只有录像无法判断跳变发生在 Launcher launch animation、starting surface 还是 App 首帧。

### 10.5 折叠或旋转后快照拉伸

检查：

- Launcher 的 `PreviewPositionHelper` 几何变换；
- 快照旋转与任务尺寸；
- 当前任务边界与显示密度；
- 启动窗口兼容性检查是否回退；
- `SnapshotDrawerUtils` 是否进入尺寸不匹配缩放路径；
- 应用新边界的缓冲区何时锁存。

### 10.6 图形内存持续上涨

分别统计：

- system_server running snapshot cache；
- 功能开关控制的 5 秒高分辨率延迟缓存；
- 持久化队列中尚未写完的 HardwareBuffer；
- Launcher thumbnail cache；
- 屏幕上的启动窗口与 Launcher 或应用窗口缓冲区；
- 其他共享 DMA-BUF 引用。

磁盘中存在大量 `.jpg` 文件，不代表这些快照都驻留在图形内存中；system_server snapshot Java 堆保持平稳，也不能排除 gralloc/DMA-BUF 压力。

## 11. 版本演进

| 平台 | 相关变化 | 分析边界 |
|---|---|---|
| Android 8 / API 26 | 引入 TaskSnapshot 基础设施，统一最近任务缩略图与保存的 Surface | 起点是 Android 8，不是 Android 9 |
| Android 10 / API 29 | TaskSnapshot 与现代 SurfaceControl/capture 路径继续演进 | 旧资料中的 `GraphicBuffer`、类名与锁行为不能直接套到 Android 17 |
| Android 12 / API 31 | BLAST、Shell transition/starting-surface 架构成为现代分析基线 | WMS 管理对象、Shell leash 与 App buffer 要分开观察 |
| Android 13 / API 33 | `Activity.setRecentsScreenshotEnabled()` 公开 | 只控制 Overview 表示，范围小于 `FLAG_SECURE` |
| Android 17 / API 37 | 当前源码锚点：`TaskSnapshotManager`、分辨率/引用跟踪、现行 SnapshotPersistQueue、Shell starting window 与 Launcher3 thumbnail UI | feature flag 与资源 overlay 仍可改变 high/low cache、格式和预加载策略 |

## 12. 源码与官方文档入口

### Android 17 platform

- [`SnapshotController.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/SnapshotController.java)：transition 捕获、snapshot manager Binder 服务与 visible Task 清理；
- [`TaskSnapshotController.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/TaskSnapshotController.java)：任务触发、高低分辨率策略、休眠捕获和持久化入口；
- [`AbsAppSnapshotController.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/AbsAppSnapshotController.java)：REAL/APP_THEME/NONE、`captureLayers`、像素格式与元数据；
- [`TaskSnapshot.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/window/TaskSnapshot.java) 与 [`TaskSnapshotManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/window/TaskSnapshotManager.java)：buffer、引用、resolution 与 Binder 客户端；
- [`SnapshotPersistQueue.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/SnapshotPersistQueue.java) 与 [`AppSnapshotLoader.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/services/core/java/com/android/server/wm/AppSnapshotLoader.java)：后台写入、压缩与磁盘恢复；
- [`TaskSnapshotWindow.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/TaskSnapshotWindow.java) 与 [`SnapshotDrawerUtils.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/window/SnapshotDrawerUtils.java)：starting surface、buffer transaction 与尺寸不匹配处理；
- [`SurfaceFlinger.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/services/surfaceflinger/SurfaceFlinger.cpp)：`captureLayersSync()`、`captureScreenCommon()` 与截图渲染。

### Android 17 Launcher3

- [`TaskThumbnailCache.kt`](https://android.googlesource.com/platform/packages/apps/Launcher3/+/refs/tags/android-17.0.0_r1/quickstep/src/com/android/quickstep/TaskThumbnailCache.kt)：Launcher 高低分辨率缓存与后台加载；
- [`TaskUiStateMapper.kt`](https://android.googlesource.com/platform/packages/apps/Launcher3/+/refs/tags/android-17.0.0_r1/quickstep/src/com/android/quickstep/recents/ui/mapper/TaskUiStateMapper.kt)：LiveTile、Snapshot、locked 与 background 状态；
- [`TaskThumbnailView.kt`](https://android.googlesource.com/platform/packages/apps/Launcher3/+/refs/tags/android-17.0.0_r1/quickstep/src/com/android/quickstep/task/thumbnail/TaskThumbnailView.kt)：静态硬件位图的 View 绘制；
- [`PreviewPositionHelper.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/packages/SystemUI/shared/src/com/android/systemui/shared/recents/utilities/PreviewPositionHelper.java)：rotation、density、letterbox、split 与 crop matrix。

### 官方说明

- [AOSP Task snapshots](https://source.android.com/docs/core/perf/task-snapshots)：Android 8.0 起源、最近任务与启动窗口共用缓冲区，以及高低分辨率配置；
- [`Activity.setRecentsScreenshotEnabled()`](https://developer.android.com/reference/android/app/Activity#setRecentsScreenshotEnabled(boolean))：API 33 的 Overview 隐私开关；
- [`WindowManager.LayoutParams.FLAG_SECURE`](https://developer.android.com/reference/android/view/WindowManager.LayoutParams#FLAG_SECURE)：安全窗口的截图与显示器约束。

## 小结

TaskSnapshot 是一次 Task surface 子树捕获及其元数据容器。Android 17 上，它至少有三种不同的显示方式：

1. Launcher 把 HardwareBuffer 包装成硬件位图，作为 Overview 静态卡片绘制；
2. Recents animation 把真实 Task surface 通过 remote leash 显示为 live tile；
3. WM Shell 把旧 TaskSnapshot 设置到独立的启动窗口 Surface，等待应用内容就绪。

分析这条管线时，应分别对齐捕获、缓存或磁盘、Binder、Launcher/Shell 几何、应用新缓冲区和目标显示器送显。将它们合并为“快照图层直接交给 HWC”的模型，会漏掉常见的卡顿、错帧和内存来源。

> 版本范围：平台与 Launcher 路径按 `android-17.0.0_r1` 核对；结论最高适用于 Android 17 / API 37。
