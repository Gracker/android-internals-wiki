---
title: "折叠屏显示管线与铰链状态渲染性能"
chapter: "2.28"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [foldable, display, rendering, jetpack-windowmanager, hinge, large-screen]
related_chapters: ["2.6", "2.12", "2.18", "2.20", "3.4", "7.12", "22.14"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-23"
drafted_date: "2026-06-24"
last_verified: "2026-06-24"
last_verified_against: "AOSP android-14.0.0_r1 + official docs (developer.android.com)"
confidence: medium
sources:
  - type: official
    path: "https://developer.android.com/guide/topics/large-screens/learn-about-foldables"
  - type: official
    path: "https://developer.android.com/reference/androidx/window/layout/FoldingFeature"
  - type: official
    path: "https://developer.android.com/about/versions/16/behavior-changes-16"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/LogicalDisplayMapper.java"
  - type: aosp
    path: "frameworks/base/core/java/android/hardware/Sensor.java (TYPE_HINGE_ANGLE)"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/display/DisplayModeDirector.java"
---

# 2.28 折叠屏显示管线与铰链状态渲染性能

折叠屏设备从 Android 12（API 31）起作为一等公民进入系统设计。与直板机相比，折叠屏在硬件通路（内屏/外屏双显示路径）、显示尺寸/分辨率动态切换、铰链传感器输入三个方面对渲染管线提出了额外要求。本节从显示硬件架构、WindowManager 折叠状态 API、转换期间 SurfaceFlinger 行为、铰链角度传感器延迟、双屏合成开销五个维度展开，给出性能观测方法和优化方向。

## 折叠屏显示硬件架构

折叠屏设备的显示硬件配置与直板机有三处结构差异。

**双显示通路**：设备同时搭载内屏（inner display，展开后使用）和外屏（cover display，折叠态使用）。两条显示通路各自连接到 SurfaceFlinger 的不同 Display 节点。内屏展开态分辨率通常在 2200×1768 到 2176×1812 之间（Samsung Galaxy Z Fold 系列、Honor Magic V 系列），像素密度高于典型手机外屏。GPU 填充率和 SurfaceFlinger 合成负载随之上升——同一帧内容在内屏全分辨率下需要填充的像素数量约为外屏的 2-3 倍。

**铰链区域像素排布**：柔性 OLED 面板在铰链弯折区域采用与主显示区不同的像素排布密度。这个区域在展开态可以正常显示内容，在折叠态则物理隐藏。双屏设备（如 Microsoft Surface Duo）的铰链区域完全无像素，用物理铰链连接两块独立面板——这种情况下 FoldingFeature 的 occlusionType 为 FULL。[已验证: 官方文档, developer.android.com/reference/androidx/window/layout/FoldingFeature]

**可变刷新率策略**：折叠屏设备的面板通常支持多档刷新率（如 1Hz/10Hz/60Hz/120Hz）。DisplayModeDirector 根据设备折叠状态选择不同的刷新率档位——展开态倾向于高刷新率（120Hz）以匹配大屏交互预期，折叠态可能降频以节省功耗。详见 §2.18 自适应刷新率。[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/display/mode/DisplayModeDirector.java]

## Jetpack WindowManager 折叠状态 API 与布局性能

Jetpack WindowManager（`androidx.window:window`）提供折叠状态感知 API，不依赖平台 API level。核心接口链路如下。

### WindowInfoTracker → FoldingFeature 回调链路

```
WindowInfoTracker.windowLayoutInfo(activity)
  → WindowLayoutInfo流(包含 DisplayFeature 列表)
    → FoldingFeature(state, orientation, bounds, occlusionType)
```

FoldingFeature 暴露四个关键属性：

- **state**：`FLAT`（完全展开平放）或 `HALF_OPENED`（中间态）
- **orientation**：`HORIZONTAL`（水平铰链，如书本翻页）或 `VERTICAL`（垂直铰链）
- **occlusionType**：`NONE`（连续柔性屏，铰链区域可显示）或 `FULL`（物理铰链，不可显示）
- **isSeparating()**：返回 `true` 时表示铰链将屏幕分成两个逻辑显示区域

[已验证: 官方文档, developer.android.com/reference/androidx/window/layout/FoldingFeature]

### 回调频率与 UI 线程协调

`WindowInfoTracker` 通过 `Activity.getWindowManager()` 和 `WindowMetrics` 推送布局信息变更。当铰链物理状态改变时，系统依次发出：

1. `WindowLayoutInfo` 更新（包含新的 FoldingFeature）
2. Configuration change（如果 manifest 声明了 `configChanges`）
3. `onConfigurationChanged()` 回调

铰链快速开合（用户在 1-2 秒内完成折叠/展开动作）时，上述回调可能连续触发 2-3 次。每次回调都会触发 `measure()` / `layout()` 重新执行。如果布局层级复杂（深度 > 10 层），measure/layout 耗时可能超过一帧预算（120Hz 下 8.33ms）。

### Activity Embedding 与折叠态切换

Activity Embedding（`androidx.window.extensions`）允许在展开态自动将两个 Activity 以 split rule 排列。折叠态切换时，split rule 需要同步更新：

- 展开态 → 折叠态：split pair 从并排变为堆叠，触发 `SplitLayout` 重新计算
- 折叠态 → 展开态：检测到 `FoldingFeature.state == FLAT` 且屏幕宽度 ≥ 600dp 时，重新激活 split rule

`SplitRule` 的 `minWidthDp` 和 `minSmallestWidthDp` 决定了 split 是否激活。如果阈值设置不当，折叠态切换会出现 split 反复激活/失活的抖动。

### Android 16 大屏强制可缩放

Android 16（API 36）对 targetSdk 36 的应用强制忽略 `screenOrientation`、`resizableActivity="false"`、`minAspectRatio`、`maxAspectRatio` 等限制，前提是显示设备 smallest width ≥ 600dp。折叠屏展开态通常满足这个条件。这意味着应用无法再通过 manifest 声明来避免折叠态下的配置变更——必须处理 `onConfigurationChanged()` 或承受 Activity 重建的开销。Android 17 移除了 `PROPERTY_COMPAT_ALLOW_RESTRICTED_RESIZABILITY` 临时豁免。[已验证: 官方文档, developer.android.com/about/versions/16/behavior-changes-16]

## 折叠/展开转换期间的渲染管线行为

折叠→展开或展开→折叠转换期间，显示管线的核心变化发生在三个层面。

### Display 设备变更与 LogicalDisplayMapper

AOSP 的 `LogicalDisplayMapper` 负责将物理 `DisplayDevice` 映射到逻辑 `LogicalDisplay`。对于折叠屏设备，`DeviceStateManager` 维护设备状态（如 `STATE_OPEN`、`STATE_HALF_OPENED`、`STATE_CLOSED`），`DeviceStateToLayoutMap` 定义每种设备状态对应的 display 布局。

转换发生时的处理序列：

1. `DeviceStateManager` 检测到铰链状态变更，发出 `onBaseStateChanged`
2. `LogicalDisplayMapper` 收到新的设备状态，查询 `DeviceStateToLayoutMap` 确定新的 display 映射
3. 如果内屏/外屏需要切换：`LogicalDisplay` 从一个 `DisplayDevice` 重映射到另一个
4. 发出 `LOGICAL_DISPLAY_EVENT_SWAPPED` 事件
5. `DisplayManagerService` 通知所有 `DisplayListener`

[已验证: AOSP android-14.0.0_r1, frameworks/base/services/core/java/com/android/server/display/LogicalDisplayMapper.java]

### SurfaceFlinger 重新协商合成策略

Display 物理分辨率或 active 区域变化后，SurfaceFlinger 需要执行：

- 重新查询 HWC 支持的 layer 数量和 format
- 重新分配 overlay plane（如果 HWC 支持多层 overlay）
- 重新计算 DisplayFrameRate 和合成管线目标帧率

转换期间可能出现 1-3 帧的丢弃——Surface resize 后的第一帧 latency 通常高于稳态 30-50%。如果应用在转换期间收到 Configuration change 且触发 Activity 重建，首帧延迟可能达到 100ms 以上。

### Configuration change 处理与避免重建

折叠/展开触发的 Configuration change 包含 `screenSize`、`smallestScreenSize`、`screenLayout`、`orientation`（如果方向也变化）。在 manifest 中声明 `android:configChanges="screenSize|smallestScreenSize|screenLayout|orientation"` 可以让 Activity 通过 `onConfigurationChanged()` 处理，避免重建。

不声明 `configChanges` 时，Activity 重建流程：`onDestroy` → `onCreate`（含 inflate、measure、layout），耗时与布局复杂度正相关。复杂页面重建可能超过 200ms（120Hz 设备约 24 帧），用户可感知为卡顿。

## 铰链角度传感器延迟与输入管线

`Sensor.TYPE_HINGE_ANGLE`（类型常量 36）提供铰链角度数据，从 Android 11（API 30）起可用。[已验证: AOSP, frameworks/base/core/java/android/hardware/Sensor.java, TYPE_HINGE_ANGLE = 36]

### 传感器到 UI 帧的延迟链路

```
HAL 传感器采样
  → SensorService (system_server)
    → SensorManager.registerListener() 回调 (app 线程)
      → Choreographer.onVsync() → doFrame()
        → View invalidate → measure/layout
          → RenderThread → GPU 渲染
            → SurfaceFlinger 合成
              → Display 显示
```

端到端延迟由各环节累积：

- 传感器采样到回调：受 `samplingPeriodUs` 控制，典型值 5-16ms（60Hz-120Hz 采样率）
- 回调到 Choreographer 对齐：如果回调到达时 Choreographer 已经过了一帧的 VSYNC，延迟增加一帧
- doFrame 到 Display：标准渲染管线延迟，详见 §2.4 Choreographer 和 §2.5 主线程/RenderThread

### 高频采样的调度压力

铰链传感器以 120Hz 采样时，每 8.33ms 触发一次 `onSensorChanged` 回调。如果回调处理逻辑执行在主线程，与 `doFrame()` 竞争 CPU 时间。建议做法：

- 使用 `Handler` 将传感器回调调度到独立线程
- 在回调中只更新轻量状态（角度值），不直接触发 `invalidate()`
- 让 Choreographer 在下一个 VSYNC 自然拾取最新角度值，而非每帧强制 push

折叠动画的流畅度直接取决于这条链路的端到端延迟。延迟超过两帧（120Hz 下约 16ms）时，动画会出现肉眼可感知的滞后。

## 双屏显示与多 Surface 合成开销

部分折叠设备在转换期间短暂同时点亮内外屏。SurfaceFlinger 需要管理两个 Display 输出的合成。

### 双 Display 合成路径

SurfaceFlinger 为每个 Display 维护独立的合成流水线。HWC overlay plane 分配在两个 Display 之间独立进行——一个 Display 的 overlay 分配不会影响另一个，但 GPU fallback 策略需要考虑总 GPU 带宽预算。

关键性能指标：

- 两块 Display 同时活跃时的合成帧率（是否都能维持目标帧率）
- Display hotplug 处理期间的帧丢弃
- `DisplayManager.getDisplays()` 返回列表变化频率和应用感知延迟

### DisplayListener 监听延迟

`DisplayManager.DisplayListener` 的 `onDisplayAdded` / `onDisplayRemoved` 回调通过 Handler 投递，延迟受 Handler 队列长度和主线程负载影响。如果应用在 `onDisplayAdded` 中执行重初始化（如创建新的 Surface、重新分配 buffer），可能进一步阻塞主线程。

`dumpsys SurfaceFlinger --display` 和 `dumpsys display` 可以查看当前 Display 配置、合成策略和 frame rate 目标，用于诊断折叠态 Display 相关的性能问题。

## 折叠屏 Continuity 动画与 App Continuity 性能

App Continuity（应用连续性）确保折叠/展开时应用状态不丢失。核心机制涉及三个层面。

### 状态保存与恢复

- **SavedStateHandle**：Jetpack ViewModel + SavedStateHandle 在 Activity 重建时保留 UI 状态
- **WindowMetrics API**：`WindowManager.getCurrentWindowMetrics()` 提供实时窗口尺寸，用于在 `onConfigurationChanged` 中调整布局
- **ViewModel 生命周期**：Configuration change 不会销毁 ViewModel（如果用 `configChanges` 避免 Activity 重建），但 Activity 重建会触发新的 ViewModel 创建（除非使用 `NonConfigurationScope`）

### 过渡动画帧预算

展开态的过渡动画（SplashScreen 退出、布局扩展）需要控制帧预算。`Activity.setLocusContext` 和 SplashScreen API 在折叠态切换时的过渡动画帧率取决于 Choreographer 的 VSYNC 对齐。Jetpack WindowManager 1.2+ 的 `AnimatedPane` 和 Material 3 的 `PaneExpansion` 动画在折叠态切换时的帧率表现取决于：

- 动画是否跑在 RenderThread（硬件加速）还是主线程（软件渲染）
- 布局变更是否触发完整 measure/layout 还是局部 invalidate
- Compose 动画是否在 `BoxWithConstraints` 中正确处理 constraint 变更

[待验证: Jetpack WindowManager 1.2+ AnimatedPane 在折叠态切换的帧率基准数据]

## 折叠屏性能测试方法

### Perfetto capture

折叠/展开转换的性能测试，需要在 Perfetto 中同时捕获以下轨道：

- **铰链传感器轨道**：`android.sensor.hinge_angle` 数据
- **SurfaceFlinger 轨道**：`SurfaceFlinger` 下的 layer timeline 和 VSYNC-sf
- **App 主线程轨道**：`main` 线程的 measure/layout/draw slice
- **RenderThread 轨道**：GPU 渲染命令提交和 fence signal
- **DisplayModeDirector 轨道**：刷新率切换事件

测量 fold transition 期间的帧时间线，重点关注：

- 转换开始后第一帧到最后一帧的时间跨度
- 丢帧数量和分布（集中在转换起始还是持续整个转换）
- Display 设备切换时 SurfaceFlinger 的 hotplug 处理耗时

### Macrobenchmark 局限

Macrobenchmark 目前没有原生的 fold 事件触发支持——无法通过代码模拟铰链物理折叠/展开。测试方案只能是：

1. 物理操作设备（人工或机械臂），同时运行 Perfetto capture
2. 使用 `adb shell cmd device_state set-state <STATE>` 模拟设备状态切换（需要 root 或 ADB 权限，且不触发铰链传感器路径）
3. 使用 UI Automator 模拟用户操作引发的间接配置变更

[待验证: Macrobenchmark 对 fold 场景的支持现状，上述限制基于 Android 14 公开 API 推断]

### dumpsys 诊断

```bash
# 查看 SurfaceFlinger 当前 Display 配置和合成策略
adb shell dumpsys SurfaceFlinger --display

# 查看 DisplayManager 的 LogicalDisplay 映射
adb shell dumpsys display

# 查看设备状态（折叠/展开）
adb shell dumpsys devicestate
```

`dumpsys display` 的输出包含 `DisplayDeviceInfo`（分辨率、刷新率、density）、`LogicalDisplay` 映射（displayId → DisplayDevice）和 `DisplayModeDirector` 状态，可以确认折叠态切换是否正确触发了 display 重映射和刷新率调整。

## 扩展

### 🔸 OEM 折叠屏渲染优化

各 OEM 在折叠屏渲染管线上有自定义扩展：

- **Samsung Flex Mode**：HALF_OPENED 状态下，Samsung 自定义 SystemUI 将底部区域作为独立控制区。这一行为通过 Samsung 的 ExtensionWindowLayoutInfo 回调暴露给应用，但渲染管线层面的实现（是否涉及独立 Surface 合成）未公开。
- **Honor/华为平行视界**：自动检测大屏展开态，将应用 UI 强制分为左右双列。实现机制可能是 WindowManagerService 层面的 Activity Embedding 注入，对应用 measure/layout 开销的影响取决于应用布局层级深度。
- **SystemUI 适配**：折叠态切换时状态栏、导航栏的位置和尺寸需要重新计算。各 OEM 的实现差异主要体现在 transition 动画的帧率和 SystemUI 重建耗时上。

[待补充: 需要 OEM 设备实测数据]

### 🔸 大屏/折叠屏与 Compose 性能交互

Compose 在折叠态的性能关注点：

- `WindowSizeClass` 变更触发 recomposition 的范围——如果 `WindowSizeClass` 作为 state 传入多个 Composable，变更会触发大范围重组
- `BoxWithConstraints` 在折叠转换时收到新的 Constraints，内部内容需要重新 measure
- `NavigationSuiteScaffold` 在大屏/折叠态切换导航组件（底部导航 → 导航轨），涉及多个 Composable 的组合/销毁
- `Crossfade` 在折叠转换时的过渡动画帧率取决于动画是否在 RenderThread 加速

控制 Compose recomposition 范围的关键手段：将 `WindowSizeClass` 读取限制在尽可能窄的 Composable 子树中，避免顶层状态变更引发全页重组。

### 🔸 桌面模式与折叠屏协同

Android 17 桌面模式（Desktop Windowing）在折叠屏展开态的行为参见 §22.14 桌面窗口化与大屏渲染性能实践。桌面模式下多窗口对 GPU 合成负载的影响、以及展开态进入桌面模式的窗口管理开销，在 §2.20 多窗口与桌面模式渲染中有基础机制说明。

> 本节已加工完成，等待 Review。


## 参考资料

### 源码调研：DisplayManagerService 多 display 管理性能边界（Android 17 / API 37）
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-06-24-android-17-displaymanagerservice-multi-display-architecture.md
- 类型：DeepResearch 调研结果
- 摘要：基于 android-17.0.0_r1 源码，深入 DMS 的 SyncRoot 单锁模型、四类 DisplayAdapter 事件投递、LogicalDisplayMapper 到 DisplayTopologyCoordinator 的完整架构。揭示 Android 17 新增 DisplayGroup/DisplayTopology 拓扑关系显式化机制，以及设备状态驱动的异步 display 转换路径。分析多 display 锁竞争边界——序列化路径的锁等待是潜在瓶颈但当前瓶颈更可能在 SF 合成。
- 注入时间：2026-06-24
- 价值：为折叠屏/多显示器渲染管线性能分析提供了 DMS 侧的系统服务级上下文，补充了 §2.28 仅有 SF/Compose 视角的不足
