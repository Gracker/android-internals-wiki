---
title: "Android XR 空间 UI 与环境资产渲染性能"
chapter: "18.22"
status: draft
applicable_versions: "Android XR / Jetpack XR SDK (2025+) - Android 16 (API 36)+"
tags: [android-xr, jetpack-xr, compose, rendering, assets, performance]
related_chapters: ["2.1", "2.10", "18.1", "18.8", "18.12", "22.3", "25.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "官方文档/AOSP结构"
sources:
  - type: official
    path: "https://developer.android.com/develop/xr"
  - type: official
    path: "https://developer.android.com/develop/xr/jetpack-xr-sdk"
  - type: official
    path: "https://developer.android.com/develop/xr/jetpack-xr-sdk/optimize-environment-assets"
  - type: official
    path: "https://developer.android.com/develop/xr/jetpack-xr-sdk/add-environments"
  - type: official
    path: "https://developer.android.com/docs/quality-guidelines/android-xr"
---

# 18.22 Android XR 空间 UI 与环境资产渲染性能

<!-- outline-start -->
## 要点

### 🔹 Android XR 在渲染体系中的位置
梳理 Android XR 与普通手机、大屏、桌面模式的关系：兼容应用可以直接进入 XR 设备，差异化应用会引入空间面板、3D 模型和空间环境。章节只讨论渲染、资源、帧预算和功耗，不展开产品形态。

### 🔹 Jetpack XR SDK 的 UI 栈边界
区分 Compose for XR、传统 View / Compose 内容、Unity 内容和系统空间化能力。整理哪些内容仍走 Android UI 渲染路径，哪些内容进入 3D / OpenXR / 引擎渲染路径。

### 🔹 空间环境资产的成本构成
依据官方环境资产文档拆出 skybox、IBL 数据、glb / ZIP 资源和文件大小约束，说明视觉质量、加载时间、内存占用和包体积之间的取舍。

### 🔹 3D 模型与纹理资源的加载预算
整理 glTF / glb 模型、纹理尺寸、材质数量、压缩格式和运行时上传成本。对照移动 GPU 的 tile-based rendering、显存带宽和纹理缓存约束。

### 🔹 视点、姿态与显示配置对帧时间的影响
围绕设备姿态、RenderViewpoint、显示配置和刷新率建立观察点，说明 XR 场景下帧时间波动为什么比普通 2D 页面更容易被感知。

### 🔹 Android XR 质量分级的性能含义
把 Android XR quality guidelines 中的 mobile、large screen、differentiated tiers 转换成性能检查项：布局自适应、输入延迟、资源加载、热管理和长时间运行稳定性。

### 🔹 工具与验证入口
列出 Android Studio、XR emulator、Perfetto、AGI、Unity profiler 的分工。每个工具只保留可复核的指标入口，不写无法验证的体验评价。

## 扩展

### 🔸 XR 与游戏 / Vulkan 渲染路径的交叉
整理 SurfaceView、OpenGL ES、Vulkan、Unity 内容进入 XR 场景后的共同问题：buffer 提交、fence 等待、GPU 队列拥塞和帧 pacing。

### 🔸 眼镜形态下 companion host device 的功耗边界
跟踪 AI glasses / wired XR glasses 场景中主机设备承担的渲染、传感器、网络和编解码成本，后续可回连功耗章节。

<!-- outline-end -->

> 本节内容待加工。
