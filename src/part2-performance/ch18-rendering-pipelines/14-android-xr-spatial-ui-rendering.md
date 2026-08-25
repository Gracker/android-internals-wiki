---
title: Android 17 / Android XR 空间 UI 与环境资产渲染性能
chapter: '18.14'
section: '18.14'
section_title: Android 17 / Android XR 空间 UI 与环境资产渲染性能
status: ready-for-review
applicable_versions: Android XR / Jetpack XR SDK Developer Preview 4；Android 17 (API 37)
last_verified: '2026-07-31'
last_verified_against: Android 17 / API 37 与 android-17.0.0_r1 公共图形栈 / Android XR Developer Preview 4 / XR Compose 1.0.0-alpha16 / XR Runtime、SceneCore、ARCore 1.0.0-beta01 / XR Projected 1.0.0-alpha10 / Compose Glimmer 1.0.0-alpha16 / Unity Android XR Extensions / OpenXR 1.1 / android17-6.18-2026-06_r6
confidence: high
tags:
- android-xr
- jetpack-xr
- compose
- rendering
- assets
- performance
related_chapters:
- '2.1'
- '2.7'
- '18.1'
- '18.4'
- '18.7'
- '22.3'
- '25.1'
sources:
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/S01_rendering_types_overview.md
  role: Android 2D panel、Surface/Buffer 与最终 display present 的证据边界
- type: internal-reference
  path: /Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Writer/rendering_pipelines/images/S05_mixed_rendering_architecture/source.md
  role: 宿主面板、独立 Surface 与多 Layer 混合场景的 Producer/Consumer 边界
- type: official
  path: https://developer.android.com/develop/xr
  role: Android XR 设备形态、SDK 与工具总入口
- type: official
  path: https://developer.android.com/blog/posts/updates-to-the-android-xr-sdk-introducing-developer-preview-4
  role: Android XR SDK Developer Preview 4 版本边界
- type: official
  path: https://developer.android.com/develop/xr/jetpack-xr-sdk
  role: Jetpack XR SDK 组成与开发预览状态
- type: official
  path: https://developer.android.com/develop/xr/jetpack-xr-sdk/ui-compose
  role: Compose for XR、SpatialPanel、Subspace 与互操作边界
- type: official
  path: https://developer.android.com/develop/xr/jetpack-xr-sdk/add-subspace
  role: Subspace 只在 spatialization enabled 时渲染及 Home/Full Space 边界
- type: official
  path: https://developer.android.com/develop/xr/jetpack-xr-sdk/add-3d-models
  role: glTF 2.0、SpatialGltfModel、SceneCore entity 与资源加载
- type: official
  path: https://developer.android.com/develop/xr/jetpack-xr-sdk/optimize-environment-assets
  role: 80 MB、10,000 vertices、200 m、KTX2 与 IBL 资产指导
- type: official
  path: https://developer.android.com/develop/xr/jetpack-xr-sdk/add-environments
  role: Full Space、SpatialEnvironmentPreference、geometry、IBL 与 passthrough
- type: official
  path: https://developer.android.com/docs/quality-guidelines/android-xr
  role: Android XR 应用等级、90/72 Hz、per-eye resolution 与启动目标
- type: official
  path: https://developer.android.com/develop/xr/jetpack-xr-sdk/get-studio
  role: Android Studio 与 XR Emulator 工具边界
- type: official
  path: https://developer.android.com/develop/xr/unity/performance/androidxr-extension-settings
  role: Application Spacewarp、Vulkan subsampling 与 late latching
- type: official
  path: https://developer.android.com/develop/xr/unity
  role: Unity/OpenXR 的 Android XR 开发入口
- type: official
  path: https://developer.android.com/develop/xr/jetpack-xr-sdk/glasses/first-activity
  role: Projected Activity 在 host 上运行及 display/audio glasses 边界
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/xr-compose
  role: XR Compose 1.0.0-alpha16、compileSdk 37、minSdk 与 experimental API
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/xr-runtime
  role: XR Runtime 1.0.0-beta01 与 suspend Session.create
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/xr-scenecore
  role: SceneCore 1.0.0-beta01、entity parent、AutoCloseable 资源与 API 变化
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/xr-arcore
  role: ARCore for Jetpack XR 1.0.0-beta01 与 RenderViewpoint API
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/xr-projected
  role: XR Projected 1.0.0-alpha10
- type: official
  path: https://developer.android.com/jetpack/androidx/releases/xr-glimmer
  role: Compose Glimmer 1.0.0-alpha16
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/xr/scenecore/GltfModel
  role: SceneCore beta01 当前只加载 binary glTF、AutoCloseable 资源语义
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/xr/scenecore/GltfModelEntity
  role: parent 默认 null 与 scene graph 可见性
- type: official
  path: https://developer.android.com/reference/kotlin/androidx/xr/arcore/RenderViewpoint
  role: left/right/mono viewpoint 的 pose、localPose 与 fieldOfView
- type: official
  path: https://registry.khronos.org/OpenXR/specs/1.1/html/xrspec.html
  role: OpenXR 1.1 frame loop、swapchain 与 runtime 协议
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java
  role: Android 2D panel 的应用起帧公共层
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp
  role: Android 2D panel 的 HWUI RenderThread 公共层
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp
  role: Android Surface Producer 的 queue/dequeue 公共层；不代表 OpenXR swapchain
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/ui/Fence.cpp
  role: Android native fence 用户空间封装
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c
  role: Android Buffer 异步完成与 wait 的通用内核边界；不描述 XR runtime 私有实现
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c
  role: 线程 Running、Runnable 与阻塞等待的通用调度边界
---

# Android 17 / Android XR 空间 UI 与环境资产渲染性能

空间 UI 的性能预算不只包含传统 2D 布局与绘制，还包括姿态更新、双目显示、3D 资产和运行时合成。应先区分 Android XR 平台、Jetpack XR SDK 与设备运行时各自负责的阶段，再为资源加载和每帧更新建立预算。

## Android XR 渲染需要区分哪些边界

Android XR 覆盖多种运行形态。手机或大屏应用可以作为 compatible panel（兼容 2D 面板）运行；XR differentiated app 可以增加 Subspace、空间面板、3D 模型、环境和感知能力；Unity/OpenXR 应用由引擎向 XR runtime 提交 swapchain image；display glasses 上的 Projected Activity 则运行在 companion host device（负责计算与连接的手机等伴随设备）。

这些形态共享 Android 进程、CPU、GPU、内存、I/O 和功耗约束，但显示终点并不相同。普通 2D 内容的应用侧仍能观察 `Choreographer`、HWUI RenderThread 和 Surface buffer；XR runtime 还要负责空间放置、视点与姿态、可能的 reprojection（依据更新后的姿态修正已渲染图像），以及向 XR 显示设备提交。Unity/OpenXR 使用 runtime 管理的 frame loop 和 swapchain，不能直接套用普通 View 的 `doFrame → DrawFrame → queueBuffer`。

分析时先回答三个问题：

1. 当前内容属于 compatible 2D panel、Jetpack XR 空间内容、Unity/OpenXR，或 Projected/Glimmer；
2. 帧时间、资源加载和显示延迟分别在哪里观测；
3. 哪些数字是 Android XR 质量目标，哪些只是资产制作建议或工具观测值。

### 当前版本与源码边界

本文的平台源码版本是 Android 17 / API 37 的 `android-17.0.0_r1`，kernel 版本是 `android17-6.18-2026-06_r6`。Jetpack XR 独立于 Android 平台 tag 发布，截至 2026-07-31 的公开版本如下：

| 组件 | 当前公开版本 | 稳定性边界 |
| --- | --- | --- |
| Jetpack Compose for XR | `1.0.0-alpha16` | 仍是 alpha；API 可能继续变化 |
| Jetpack SceneCore | `1.0.0-beta01` | beta；entity parent、资源生命周期与动画 API 仍在变化 |
| ARCore for Jetpack XR | `1.0.0-beta01` | beta；`RenderViewpoint`、tracking API 仍需按版本锁定 |
| Jetpack XR Runtime | `1.0.0-beta01` | beta；`Session.create` 已改为 suspend function |
| Jetpack XR Projected | `1.0.0-alpha10` | audio/display glasses 投射 API 仍是 alpha |
| Jetpack Compose Glimmer | `1.0.0-alpha16` | 2026-07-29 更新；透明 display glasses UI 仍是 alpha |
| Android XR SDK 总体 | Developer Preview 4 | 官方仍将整组 SDK 标为开发中 |

Compose for XR 从 `1.0.0-alpha14` 起将 `compileSdk` 更新到 API 37，并要求至少 AGP 9.2.0。alpha16 把库的 `minSdk` 降到 24，但官方同时说明 Jetpack XR API 运行时仍要求 API 34。这三项条件要分开理解：`compileSdk 37` 决定编译时可见 API，manifest minSdk 决定安装兼容范围，XR runtime 条件决定功能能否运行。使用 alpha16 时应按对应 release notes 配置构建环境。本文只采用当前文档仍存在的概念，不用早期 alpha 类名推断长期 API。

公开 AOSP tag 可以验证 Android 的 HWUI、Surface、BufferQueue、fence 和调度公共层，但不能据此补写未公开的 XR compositor 内部调用链。本文对 XR runtime 的描述只覆盖 Jetpack、Unity/OpenXR 与质量文档公开的协议和责任边界。

## Android XR 在渲染体系中的位置

Android XR 质量指南把 Android 应用分成 compatible mobile、compatible large screen 和 differentiated 三档。工程分析还应单列 Unity/OpenXR 与 Projected/Glimmer，因为它们使用不同帧循环和设备边界。

| 应用形态 | 内容如何进入 XR | 优先观察点 |
| --- | --- | --- |
| compatible mobile app | 现有 Activity 作为 2D 面板运行 | App 主线程、HWUI、SurfaceFrame、输入、启动与 resize |
| compatible large screen app | 大屏自适应 Activity 作为可调整面板运行 | 2D 路径，加窗口尺寸、外设输入、多任务和状态恢复 |
| Jetpack XR differentiated app | Subspace、SpatialPanel、SceneCore entity、环境等进入 XR scene | 2D 面板 Buffer、Subspace layout、模型/纹理、scene attach、XR runtime |
| Unity / OpenXR | 引擎渲染 runtime swapchain image，经 `xrEndFrame` 等边界交给 runtime | simulation、render thread、GPU、swapchain wait/release、spacewarp/late latching |
| Projected / Compose Glimmer | Activity 在 host phone 运行，体验投射到 audio/display glasses | host CPU/GPU、projected display 状态、连接、眼镜输入与远端 present |

compatible panel 仍沿用 2D 应用生产路径，不会自动变成 3D 引擎应用。但应用 buffer 生成完成也不代表 XR 显示完成。Android App FrameTimeline 可以定位应用侧 SurfaceFrame；XR runtime 的姿态更新、空间合成、reprojection 与光学显示还需要 runtime、引擎或设备专用证据。

下面的概念图只划分责任，不表示公开 API 承诺固定进程、线程或 compositor 名称：

```text
2D compatible / SpatialPanel
App UI → HWUI/Surface Buffer → XR scene/runtime → XR compositor/display

Jetpack XR 3D
App state → Subspace/SceneCore entity → model/material resources
          → XR scene/runtime → XR compositor/display

Unity/OpenXR
Simulation → RenderThread/GPU → OpenXR swapchain image
           → xrEndFrame → XR runtime/reprojection → display

Projected glasses
Host Activity/Compose → projected session/transport → glasses display/input
```

这四条路径可能共享 GPU 和显示资源，也可能由不同 runtime 实现。trace 分析应从本帧的 producer、提交目标 surface/swapchain、姿态责任方和最终 present 责任方开始，不能只按框架名寻找最长 slice。

对 compatible panel 与 `SpatialPanel`，可以复用普通 Android 窗口的证据链，追到 `Choreographer`、HWUI、dequeue/queue、应用 Surface buffer 和 transaction。证据到达 XR scene/runtime 接收边界后，就要停止套用标准手机链路；公开文档没有给出固定的 XR compositor 进程、latch slice 或最终 present fence 名称。

`SpatialExternalSurface`、SceneCore `SurfaceEntity`、视频和 Camera 内容应按独立 producer/Surface 记录。它们可能与 2D panel 共享 GPU、带宽和 runtime 合成预算，但 panel 的 FrameTimeline 不能覆盖独立 Surface 的完整生产节奏。该 Surface 是否对应可见的 SurfaceFlinger Layer，也要通过设备 trace 或 Layer 树确认，不能只凭 API 类名推断。

## Jetpack XR SDK 的 UI 栈边界

Jetpack XR SDK 是一组覆盖 UI、scene、感知和 projected device 的库，不是单一渲染器：

| 内容类型 | 主要 API / 库 | 性能观察点 |
| --- | --- | --- |
| 2D View / Compose | 普通 Activity 内容、View interoperability、`SpatialPanel` | UI thread、recomposition/layout、HWUI、面板 Buffer cadence |
| Subspace layout | `Subspace`、`SpatialRow`、`SpatialColumn`、orbiter | Subspace measure/layout、实体数量、尺寸/位置更新频率；orbiter 是附着在空间组件边缘附近的 UI |
| 3D 模型 | `SpatialGltfModel`、`GltfModel.create()`、`GltfModelEntity` / `SceneCoreEntity` | I/O、解析、纹理转码/上传、首次可见、动画与材质成本 |
| 外部媒体 Surface | `SpatialExternalSurface`、SceneCore `SurfaceEntity` | codec/Camera Producer、surface size、stereo shape、Buffer/fence |
| 空间环境 | `SpatialEnvironment`、glTF geometry、skybox、IBL ZIP | 环境切换、资产常驻、纹理带宽、Full Space；IBL 是 Image-Based Lighting（基于图像的光照） |
| 感知 | ARCore for Jetpack XR、`ArDevice`、`RenderViewpoint`、anchors/planes/depth | tracking state、数据新鲜度、感知 CPU、业务更新频率 |
| Display glasses | Compose Glimmer、Jetpack Projected | host Activity、projected display capability、输入与连接 |

`Subspace` 是 Compose for XR 中容纳空间布局的区域，只在 spatialization enabled 时渲染；在 Home Space 或非 XR 设备上，其中内容可能被忽略。`SpatialPanel` 把 2D 内容放进空间布局，`SceneCoreEntity` 把 SceneCore 实体接入 Compose for XR，`SpatialExternalSurface` 则承载媒体或其他 Surface producer。三者的 producer、布局和消费路径不同，不能只按“空间组件”合并统计。

截至 alpha16，`SpatialGltfModel` 的加载与动画 API 仍在调整，动画相关 API 还被标为 experimental。SceneCore beta01 中，`GltfModelEntity.create()` 的 parent 默认值是 `null`。scene graph（用父子关系组织空间实体的场景树）只有挂入可见根节点的实体才会参与对应场景；若要显示模型，应在创建时传入 `session.scene.activitySpace` 等 parent，或随后设置 `entity.parent`。entity 创建成功只能证明对象存在，不能证明资源已经挂入可见 scene graph。

`SpatialGltfModelState`、SceneCore `GltfModel` 与 `ImageBasedLightingAsset` 等资源类型提供 `AutoCloseable` 生命周期，表示调用方需要在不再使用时显式 `close()`。离开场景时还要解除 parent、清理强引用；仅仅加载完成或把 entity 从场景中移除，都不能证明底层模型、纹理等资源已经释放。业务代码必须锁定具体依赖版本，诊断文档也应记录 `xr.compose`、`xr.runtime`、`xr.scenecore`、`xr.arcore`、`xr.projected` 与 `xr.glimmer` 的完整版本。

## 空间环境资产的成本构成

`SpatialEnvironment` 管理应用的空间环境偏好。按 SceneCore beta01 的当前模型，`SpatialEnvironmentPreference` 接收一个 `ImageBasedLightingAsset` 和一个 glTF geometry。用户直接看到的 skybox texture（包围场景的远景纹理）放在 geometry 资产中，独立 IBL ZIP 用于 lighting、reflection 与 specular（镜面反射高光）计算。每份偏好最多提供一份 lighting asset 和一份 geometry。环境只在 Full Space 可见；passthrough 是相机画面构成的现实世界视图，达到 full opacity 时会完全遮住 geometry。

从 Jetpack XR alpha04 起，官方建议把可见环境与 IBL 数据拆开：

| 资产 | 用途 | 官方建议的边界 |
| --- | --- | --- |
| `.glb` / `.gltf` | 环境 geometry 与用户看到的 skybox texture | geometry 文件建议控制在 80 MB 或更小；近处 mesh 更密、远处更稀；每个 geometry patch 不超过 10,000 vertices |
| IBL ZIP | lighting、reflection、specular 计算 | 由 HDR EXR（高动态范围图像格式）经 `cmgen` 生成；示例 EXR 为 1024 × 512 |
| black PNG | IBL 生成流程中的优化纹理 | 示例为 100 × 50，用户不会直接看到 |

80 MB 与 10,000 vertices 是内容制作建议，不是 runtime parser 的拒绝阈值。超过建议值可能增加解析、内存、GPU 和功耗成本，但不能仅凭文件大小判定某帧一定卡顿。

拆分可见 skybox 与 lighting map 后，两者可以独立选择分辨率，避免为了光照计算读取过大的可见纹理，从而降低纹理带宽和功耗。自定义环境含 3D 对象时，缺少匹配 IBL 可能导致过亮、过暗，或反射方向与环境不一致。

官方将环境 view distance 写为距用户 200 m，并建议把用户放在约 1.5 m 高的位置。200 m 是环境制作与渲染的可见距离指导，不代表感知传感器量程；1.5 m 用于减少较大 UI 与地面穿插，也不是平台 API 上限。

## 3D 模型与纹理资源的加载预算

Jetpack XR 的内容规范支持 glTF 2.0，作者工具常输出 `.gltf` 或 `.glb`；SceneCore beta01 的 `GltfModel.create()` API 文档同时注明，当前 loader 只支持 binary glTF（`.glb`）。Compose for XR 可使用 `SpatialGltfModel`；SceneCore 路径先通过 `GltfModel.create()` 加载，再用 `GltfModelEntity.create(..., parent = session.scene.activitySpace)` 或后续设置 parent 接入 scene graph。部分 3D 内容只在 Full Space 可见，创建前应检查 `SpatialCapability.SPATIAL_3D_CONTENT`。

加载预算可以按四段拆：

| 阶段 | 常见成本 | 排查入口 |
| --- | --- | --- |
| 文件读取与交付 | APK/asset/URI、压缩、Play Asset Delivery、冷缓存 | I/O trace、下载/解包时间、资源命中 |
| 解析与对象创建 | glTF chunk、node、mesh、material、animation、对象分配 | CPU、allocation、GC、加载 coroutine |
| 纹理转码与 GPU 上传 | KTX2/Basis 压缩纹理、mipmap（按距离选用的多级纹理）、纹理尺寸、材质与 sampler | GPU memory/counter、upload、带宽、首次 shader |
| scene attach 与首帧 | Entity 创建、Subspace measure/layout、Full Space capability | 首次可见时间、layout、runtime submit |

压缩后的 `.glb` 或 KTX2 文件大小不等于 GPU resident size（解压、转码后实际常驻 GPU 内存的大小）。运行时转码格式、mip chain、每眼目标、材质数量和 runtime 缓存都会改变内存占用。官方建议环境 glb 使用 mipmaps 与 KTX2，主要收益涉及纹理采样、远近层级、内存带宽和包体；仍需在目标 GPU 上确认最终格式与常驻量。

大模型宜异步预取，但在启动初期一次性加载全部资源，会把启动、峰值内存与热压力前移。工程上应按可见优先级加载：

1. 首个可交互面板与必要模型；
2. 用户视野内近期会出现的纹理和动画；
3. 远处环境或低概率内容；
4. 离开场景后可以释放或降级的缓存。

资源加载、scene attach 与首帧 present 要分别打点。若只记录 `GltfModel.create()` 返回时刻，会漏掉 GPU upload、shader warm-up（首次编译或准备 shader）和首次被 runtime 采用的时间。解除 entity parent 也只改变场景挂载关系；还要处理 `AutoCloseable` 资产，才能建立纹理与模型资源的释放边界。

## 视点、姿态与显示配置对帧时间的影响

XR 需要同时观察四条时间线：

| 时间线 | 要回答的问题 |
| --- | --- |
| simulation / UI | 本帧状态、输入和动画是否及时更新 |
| App GPU | 当前 eye buffer 或 panel buffer 是否在 deadline 前完成 |
| XR runtime | pose 更新、spacewarp/reprojection、空间合成是否采用了 App 本帧 |
| display | runtime 提交后何时扫描与显示；光学响应是否另有延迟 |

应用完成一帧，不代表用户已经看到与该姿态对应的画面。spacewarp/reprojection 可能基于上一张 App 图像和更新后的运动信息生成中间显示帧，因此显示可以继续刷新，而 App 无须为每个 display refresh 生产全新 render frame。引擎 FPS、App FrameTimeline、runtime synthesized cadence 与 display refresh rate 需要分开记录。

ARCore for Jetpack XR 的 `ArDevice` 提供设备 pose，`RenderViewpoint.left/right/mono` 的 state 提供 viewpoint 的 `pose`、`localPose` 与 `fieldOfView`（视场角）。`pose` 与 `localPose` 是不同参考空间中的位姿表达，应用需要按 API 契约选择。它们为渲染提供输入，却不说明 runtime 何时 latch（锁定并采用）这份 pose，也不提供最终 motion-to-photon（头部运动到对应光子进入眼睛）的延迟。读取频率、坐标空间和使用该 pose 的 render frame 必须在应用侧对齐；没有公开时间戳时，不能声称得到了精确的跨层 pose age。

Unity Android XR Extensions 提供三类不同优化：

| 能力 | 作用 | 不能省略的验证 |
| --- | --- | --- |
| Application Spacewarp | 使用 motion vector（像素运动方向与幅度）和 depth 合成交替帧，降低 App GPU 渲染频率 | motion vector/depth 正确性、合成伪影、App 与 display cadence |
| Vulkan subsampling | 借助 Fragment Density Map（区域采样密度图）让不同区域以不同密度渲染/采样 | 目标设备支持、画质、GPU/带宽收益 |
| late latching | 在帧生成后段更新 head pose，减少渲染使用的姿态与显示时姿态之间的时间差；官方描述收益可接近一个 frame time | 标记节点正确、runtime 支持、MTP 或可替代指标 |

这些能力属于 Unity/OpenXR 引擎路径，不是普通 Compose panel 的开关。各项优化可能作用于同一段时序或改变彼此前提，理论收益不能简单相加成固定延迟数值。

## Android XR 质量分级的性能检查项

官方给出的 90/72 Hz、per-eye resolution 和启动目标属于 Android XR-differentiated quality requirements，用于质量评估，不是所有 compatible 2D panel 的设备规格承诺。

| 检查项 | compatible mobile / large screen | XR-differentiated |
| --- | --- | --- |
| 布局 | 核心任务可完成；large screen app 遵守对应 Tier 指南 | Subspace、面板、环境和 3D 内容适配 Full/Home Space |
| 输入 | Android 常规输入与必要的外设路径 | natural hand input、raycast/gesture 等适用能力 |
| 渲染 | 2D App 自身 deadline、resize 和输入响应 | 每帧 `<11.1 ms @ 90 Hz`、`<13.8 ms @ 72 Hz` |
| 分辨率 | 由兼容面板与设备策略决定 | 至少 `1856 × 2160` per eye |
| 启动 | 记录 cold/warm 与 first interaction | mean cold `<2 s`、mean warm `<1 s` |
| 稳定性 | crash、ANR、恢复 | 长会话、tracking/runtime 异常、内存与 thermal |

11.1 ms 与 13.8 ms 是整个 App render budget 的目标量级，不表示主线程可以独占这段时间。CPU simulation、render thread、GPU、swapchain wait 和 runtime 提交会共同消耗预算；native XR App 还需使用引擎或 OpenXR timing 证据分段定位。

“每眼 1856 × 2160”也不能直接换算成两次完整 render pass。multiview（一次提交处理双眼视图）、foveation（中心区域高质量、外围降低质量）、subsampling、spacewarp 与设备 compositor 都可能改变实际着色像素和 pass 数，必须通过 AGI、引擎 frame debugger 或 GPU counter 观察目标设备。

## 工具与验证入口

单个工具无法覆盖从 App 到光学显示的完整路径。每次复盘都应明确工具能看到的阶段和无法证明的阶段。

| 工具 | 适合确认的问题 | 不适合直接判断的事项 |
| --- | --- | --- |
| Android Studio + XR Emulator | capability、布局、Home/Full Space、输入与功能验证 | 真实 GPU、传感器、thermal、光学与 MTP |
| Perfetto / FrameTimeline | Android 线程、调度、I/O、HWUI panel、部分 GPU/SF 证据 | 未公开的 XR compositor 全时序与 panel 光学响应 |
| AGI / GPU counter | 支持设备的 render pass、shader、纹理、带宽与 GPU 时间 | 无目标驱动支持时无法观测；GPU 时间也不等于 MTP |
| Unity Profiler / Frame Debugger | simulation、render thread、URP、资源、spacewarp 输入 | Android 调度、系统 I/O、host thermal 的完整原因 |
| OpenXR/厂商 runtime 工具 | swapchain、runtime timing、reprojection、pose | 普通 View/Compose 内部重组与业务调用栈 |
| Winscope / SurfaceFlinger dump | Android Window/Layer、resize、可见性、panel Buffer | SceneCore entity graph 与 XR runtime 最终合成 |

### 推荐的单帧检查顺序

1. 记录设备形态、系统版本、显示 refresh rate、Home/Full Space、passthrough；
2. 记录 Jetpack XR 或 Unity/OpenXR 的准确 package 版本与开关；
3. 识别目标内容属于 Android panel、external surface、SceneCore entity 或 OpenXR swapchain；
4. 对齐 App CPU、render thread、GPU submit 与 Buffer/swapchain 边界；
5. 查 runtime 是否采用当前帧，是否使用 spacewarp/reprojection；
6. 查 display cadence、thermal、CPU/GPU frequency 和长会话趋势；
7. 分别记录 App render miss、runtime miss、tracking stale（姿态或感知数据过旧）和显示延迟。

公开文档没有承诺统一的 Android XR Perfetto slice 名。在 trace 中按 `XR` 关键字搜索不到事件，不能证明 runtime 没有工作；应从目标线程、surface/swapchain、GPU 和设备工具逐层建立证据。

每份报告至少保留设备类型、系统 build、Jetpack XR/Unity package、refresh mode、空间模式、passthrough、模型/环境版本、纹理上限、采集工具版本与复现动作。

## XR 与游戏 / Vulkan 渲染路径的交叉

Unity for Android XR 建立在 OpenXR 之上，Android XR Extensions 进一步提供 spacewarp、Vulkan subsampling 和 late latching 等能力。引擎路径仍需检查 18.5、18.6、18.12 的公共问题：simulation 是否按时，GPU queue 是否积压，swapchain image 是否及时 acquire/release，fence 是否延后，frame pacing 是否匹配 runtime 节奏。

OpenXR 的 `xrWaitFrame → xrBeginFrame → acquire/wait swapchain image → render → release image → xrEndFrame` 是应用与 runtime 的关键协议边界。`xrWaitFrame` 返回 predicted display time 等帧调度信息，应用在 `xrBeginFrame` 后生成内容，释放 swapchain image 后再通过 `xrEndFrame` 提交 composition layers（runtime 要合成的空间图层描述）。这套协议不是 Android `BufferQueue` API；trace 中即使都出现 acquire、wait、release，也要按对象类型区分。

XR 还增加姿态新鲜度和用户舒适度约束。Unity Profiler 的平均 FPS 只能说明引擎吞吐的一部分；还要结合 slow frame 分布、spacewarp 状态、runtime cadence、tracking 与 Android 系统调度。

## 眼镜形态下 host device 的功耗边界

设备类型需要分开记录：

- XR headset / wired XR glasses：Compose for XR、SceneCore、Unity/OpenXR 文档覆盖的空间/沉浸路径；
- audio/display glasses：Jetpack Projected 让应用运行在 companion host（如 Android phone），Compose Glimmer 为透明 display glasses 提供 UI；
- audio glasses 没有可视 display 时，应用应按 capability 降级为音频或其他交互。

Projected 场景要同时记录 host 与 glasses 两端：

| host device | glasses / projected device |
| --- | --- |
| Activity 生命周期、Compose、CPU/GPU、相机/编解码、网络、thermal | display on/off、输入、camera/sensor、连接、显示 cadence、设备功耗 |

host 上按时生成帧，不能证明传输和 glasses present 也按时；眼镜发热也不能直接归因于 host GPU。两端时钟若没有经过同步，应使用可关联的 event id 与往返测量，避免直接拿不同设备的原始 timestamp 相减。

## 复核清单

- [ ] 平台版本不高于 Android 17，平台源码锚点为 `android-17.0.0_r1`；
- [ ] Jetpack XR / Unity / OpenXR package 使用完整版本号；
- [ ] compatible panel、Subspace、external surface、OpenXR 与 Projected 路径已区分；
- [ ] App SurfaceFrame 没有被当作最终 XR present；
- [ ] App render rate、runtime/display refresh 与 spacewarp cadence 已区分；
- [ ] 90/72 Hz 与 per-eye resolution 明确标为 differentiated quality target；
- [ ] glb 80 MB、10,000 vertices 与 1.5 m 明确标为制作指导，200 m 标为环境 view distance；
- [ ] I/O、解析、纹理转码/上传、scene attach、首次 present 分别打点；
- [ ] SceneCore entity 已设置可见 parent，`AutoCloseable` 模型与 IBL 资源有明确释放点；
- [ ] `RenderViewpoint` 数据没有被误写成 runtime pose latch 保证；
- [ ] emulator 数据没有替代真机 GPU、thermal、tracking 或光学延迟；
- [ ] host phone 与 projected glasses 的性能和功耗分开记录。

## 参考资料

- [Develop with the Jetpack XR SDK](https://developer.android.com/develop/xr/jetpack-xr-sdk)
- [Android XR SDK Developer Preview 4](https://developer.android.com/blog/posts/updates-to-the-android-xr-sdk-introducing-developer-preview-4)
- [Android XR app quality guidelines](https://developer.android.com/docs/quality-guidelines/android-xr)
- [Jetpack Compose for XR release notes](https://developer.android.com/jetpack/androidx/releases/xr-compose)
- [Jetpack XR Runtime release notes](https://developer.android.com/jetpack/androidx/releases/xr-runtime)
- [Jetpack SceneCore release notes](https://developer.android.com/jetpack/androidx/releases/xr-scenecore)
- [ARCore for Jetpack XR release notes](https://developer.android.com/jetpack/androidx/releases/xr-arcore)
- [Jetpack XR Projected release notes](https://developer.android.com/jetpack/androidx/releases/xr-projected)
- [Jetpack Compose Glimmer release notes](https://developer.android.com/jetpack/androidx/releases/xr-glimmer)
- [Develop spatial UI with Compose for XR](https://developer.android.com/develop/xr/jetpack-xr-sdk/ui-compose)
- [Add a Subspace](https://developer.android.com/develop/xr/jetpack-xr-sdk/add-subspace)
- [Add 3D models](https://developer.android.com/develop/xr/jetpack-xr-sdk/add-3d-models)
- [Add spatial environments](https://developer.android.com/develop/xr/jetpack-xr-sdk/add-environments)
- [Optimize environment assets](https://developer.android.com/develop/xr/jetpack-xr-sdk/optimize-environment-assets)
- [Android XR Extensions performance settings for Unity](https://developer.android.com/develop/xr/unity/performance/androidxr-extension-settings)
- [Projected Activity for audio and display glasses](https://developer.android.com/develop/xr/jetpack-xr-sdk/glasses/first-activity)
- [OpenXR specification](https://registry.khronos.org/OpenXR/specs/1.1/html/xrspec.html)
- AOSP Android 17, [`Choreographer.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/view/Choreographer.java)、[`DrawFrameTask.cpp`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/DrawFrameTask.cpp)、[`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp) 与 [`Fence.cpp`](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/ui/Fence.cpp)
- Kernel common `android17-6.18-2026-06_r6`, [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c) 与 [`sched/core.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/core.c)
