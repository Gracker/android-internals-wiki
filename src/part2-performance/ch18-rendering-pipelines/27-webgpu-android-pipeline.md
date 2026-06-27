---
title: "WebGPU on Android 渲染与计算管线"
chapter: "18.27"
status: draft
applicable_versions: "Android 7.0 (API 24) - Android 17 (API 37)"
tags: [webgpu, gpu, dawn, androidx, compute, rendering, vulkan, opengl-es]
related_chapters: ["2.14", "14.8", "18.8", "18.9", "18.11"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-27"
gap_source: "研究素材"
---

# 18.27 WebGPU on Android 渲染与计算管线

<!-- outline-start -->
## 要点

### 🔹 Jetpack WebGPU 库架构
androidx.webgpu（2025 年进入 AndroidX 仓库）是 WebGPU 标准的 Kotlin bindings，通过 @FastNative JNI 调用预编译的 Dawn 原生库（libwebgpu_jni.so）。调用链：Kotlin GPU/Adapter/Device → @FastNative external fun → JNI → Dawn → Vulkan/OpenGL ES driver。库本身 minSdk = 24（Android 7.0），与系统版本解耦——开发者通过 App 依赖管理升级，不依赖 targetSdk 或系统更新。

### 🔹 FeatureLevel 双 Profile 与 Backend 选路
源码 FeatureLevel.kt 定义两档：Compatibility（0x1，对应 OpenGL ES 3.1+ 后端）和 Core（0x2，对应 Vulkan 后端）。Android 设备实际只命中 Vulkan 或 OpenGLES 两种 BackendType。Core Profile 性能上限显著高于 Compatibility Profile——GPU 限制（GPULimits vs GPUCompatibilityModeLimits）、支持的 buffer 纹理大小、绑定组数量等均有数量级差异。

### 🔹 Dawn 原生库与 AOSP 集成路径
Dawn 源码位于 `external/dawn/dawn.git`（Chromium 项目 fork），Jetpack 通过 prebuilt 形式发布。Dawn 的 Vulkan 后端在 Android 上的设备兼容性依赖 Vulkan 1.1+ 驱动；OpenGLES 后端兜底覆盖老旧 GPU 设备。Android 17 设备大多配备 Vulkan 1.3+ 驱动，Core Profile 可用率较高。

### 🔹 WebGPU vs Vulkan 原生 API 性能边界
WebGPU 相比 Vulkan 原生 API 引入的额外开销：(1) Dawn 内部的状态追踪与命令验证层，(2) Kotlin→JNI 上下文切换（@FastNative 降低但未消除），(3) WebGPU 标准的安全约束（绑定组边界检查、纹理格式验证）。在 ML 推理、图像处理等典型 GPGPU 场景中，WebGPU 与原生 Vulkan 的差距约 5-15%，具体取决于 workload 类型和 batch size。

### 🔹 WebGPU Compute Shader 在 Android 上的实际表现
WebGPU Compute Shader 的 dispatch 性能受三个因素影响：(1) Device lost 时的错误恢复机制开销，(2) Pipeline layout 兼容性验证（Core vs Compatibility Profile 路径不同），(3) Buffer usage flags 限制（GPUBufferUsage.STORAGE 在 Compatibility Profile 下的最大 binding 数量受限）。

### 🔹 适用场景与替代 API 选型矩阵
WebGPU on Android 适合的场景：(1) 跨平台 GPU compute（同一代码跑在 Android/iOS/Desktop），(2) WebView 内嵌 3D/计算渲染（替代 WebGL 2.0），(3) 图片/视频处理管线中的 GPU 加速步骤。不适合的场景：(1) 极低延迟的游戏渲染（用 Vulkan/OpenGL ES 原生），(2) 需要 Android 平台特定 GPU 扩展（WebGPU 标准不覆盖），(3) 启动阶段 GPU 初始化（Dawn 库加载有 50-100ms 开销）。

## 扩展

### 🔸 WebGPU 与 RenderDoc/AGI GPU 调试工具兼容性
Dawn 后端的 Vulkan 路径可被 RenderDoc 和 AGI（Android GPU Inspector）捕获。OpenGLES 后端可被 AGI 捕获但 RenderDoc 支持有限。调试时需在 Adapter 请求中设置 label 字段辅助工具识别。

### 🔸 Dawn 内部线程模型与 Android 线程交互
Dawn 的默认线程模型是 single-threaded（所有 GPU 命令在同一线程提交），但 AndroidX 封装提供了 async queue 支持。多线程使用 WebGPU Device 需要遵守 WebGPU 规范的线程安全约束——Device 本身可跨线程引用，但 Queue 和 CommandEncoder 是单线程的。

<!-- outline-end -->

> 本节内容待加工。
