---
title: "Layout Inspector 与 ViewDebug 布局调试"
chapter: "14.16"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [layout-inspector, viewdebug, android-studio, compose, view-hierarchy]
related_chapters: ["7.12", "14.1", "22.1", "22.3"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "素材驱动/官方文档/AOSP结构"
sources:
  - type: official
    path: "https://developer.android.com/studio/debug/layout-inspector"
  - type: official
    path: "https://developer.android.com/develop/ui/compose/tooling/debug"
  - type: official
    path: "https://developer.android.com/develop/ui/views/layout/improving-layouts/optimizing-layouts"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewDebug.java"
  - type: aosp
    path: "frameworks/base/core/java/android/view/ViewRootImpl.java"
  - type: obsidian
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-01-viewdebug-layout-trace.md"
  - type: obsidian
    path: "source/juejin-android/2026-05-01/2026-05-01-75967106-2026年了Android开发该如何调.md"
---

# 14.16 Layout Inspector 与 ViewDebug 布局调试

<!-- outline-start -->
## 要点

### 🔹 Layout Inspector 解决的问题
定位 Layout Inspector 在 UI 走查、层级分析、属性查看、源码跳转和 Compose 调试中的位置，区分它与 CPU/Memory Profiler、Perfetto、Winscope 的边界。

### 🔹 Live Layout Inspector 与 snapshot 工作流
梳理连接设备、选择进程、查看组件树、导出 snapshot、离线复查的流程，并说明 debug / release / profileable 构建下可见信息的差异。

### 🔹 View 层级、属性与 3D/层级视图
说明 View 树、属性面板、绝对位置、尺寸、约束关系和层级深度如何用于定位布局错位、遮挡、点击事件被覆盖等问题；补充 Android Studio Panda 2 起 3D 模式移除的版本边界。

### 🔹 Compose UI 调试与重组计数
覆盖 Layout Inspector 对 Compose 节点、semantics、源码跳转、recomposition / skipped counts 的支持条件，说明 API 29+ 与 Compose 1.2.0+ 的版本要求。

### 🔹 ViewDebug 与 AOSP 属性导出机制
从 `ViewDebug.@ExportedProperty`、`@CapturedViewProperty`、`dumpCapturedView()` 解释 Layout Inspector 能看到哪些属性，以及为什么部分运行时状态无法直接展示。

### 🔹 RenderNode / DisplayList 与 invalidate 调试线索
把 `View.invalidate()`、`ViewRootImpl.scheduleTraversals()`、RenderNode DisplayList 重新录制和硬件加速局部更新串起来，帮助读者用调试工具判断“布局问题”还是“绘制/脏区更新问题”。

### 🔹 第三方布局调试工具的适用边界
比较 AYA、Layout Inspector、uiautomator dump、Accessibility 视图抓取的可见范围、权限要求、release App 支持情况和数据精度，避免把工具能力误判为平台事实。

## 扩展

### 🔸 Layout Inspector 连接失败排查
记录常见失败点：Android Studio 版本、ADB 连接、进程 profileable、Compose tooling 依赖、设备系统版本和厂商调试限制。

### 🔸 UI 走查中的 px / dp / density 换算
补充从绝对像素坐标回推 dp、状态栏/导航栏 inset、窗口缩放、多窗口模式对坐标的影响。

### 🔸 与 Perfetto / FrameTimeline 联合诊断
说明当 Layout Inspector 只能看到静态层级时，如何切到 Perfetto 验证 `measure`、`layout`、`draw`、FrameTimeline jank 与主线程耗时。

<!-- outline-end -->

> 本节内容待加工。
