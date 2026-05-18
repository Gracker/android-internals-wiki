---
title: "Winscope 与窗口/合成状态可视化调试"
chapter: "14.15"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [winscope, surfaceflinger, windowmanager, perfetto, tracing, rendering, input]
related_chapters: ["2.6", "2.12", "2.13", "2.16", "3.1", "13.3", "13.10", "14.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-19"
gap_source: "官方文档/每日信息/AOSP工具文档"
sources:
  - type: official
    path: "https://source.android.com/docs/core/graphics/tracing-win-transitions"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/capture/winscope"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/capture/adb"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/analyze/sf"
  - type: official
    path: "https://source.android.com/docs/core/graphics/winscope/analyze/search"
  - type: daily-info
    path: "intake/daily-info/2026-05-19.md"
---

# 14.15 Winscope 与窗口/合成状态可视化调试

<!-- outline-start -->
## 要点

### 🔹 Winscope 的证据边界
梳理 Winscope 能提供的状态证据：Window Manager 状态、SurfaceFlinger layer 状态、SurfaceControl transaction、窗口转场、ViewCapture，以及这些证据不能替代 CPU 调度、fence 等时间线分析的边界。

### 🔹 采集入口与 trace 类型选择
区分网页端 Winscope 采集、adb 命令采集和离线 dump；说明 Window Manager、SurfaceFlinger、Transactions、Transitions、ViewCapture、virtual display 等开关分别适合哪类问题。

### 🔹 窗口、layer、输入焦点的对照方法
建立 Window Manager 窗口树、SurfaceFlinger layer 树、输入焦点和触摸区域之间的对照关系，用于定位点击无响应、窗口被遮挡、layer 层级异常、焦点错误等问题。

### 🔹 与 Perfetto / AGI 的分工
说明 Winscope 状态快照、Perfetto 时间线、AGI SurfaceFlinger Tracks 之间的分工：状态异常用 Winscope 定位，耗时归因用 Perfetto 或 AGI 补证。

### 🔹 典型排障路径
覆盖白屏/黑屏、启动后首帧未出现、转场动画异常、横竖屏切换错位、系统窗口遮挡、PIP/自由窗口场景 layer 错位等场景的观察顺序。

### 🔹 Android 版本、权限与数据保真边界
整理不同 Android 版本中 Winscope trace 支持范围、debuggable/userdebug 限制、ring buffer 截断、SurfaceFlinger 仅在几何变化时记录新状态等边界。

## 扩展

### 🔸 Winscope Search 与 SQL 视图
补充 SurfaceFlinger、Transactions、Transitions、ViewCapture 专用 SQL view 的搜索方法，用于批量定位指定 layer、窗口 token、transition id 或 transaction。

### 🔸 与 dumpsys window / dumpsys SurfaceFlinger 的互证
整理 adb dumpsys 文本输出、proto dump 和 Winscope 可视化之间的对应关系，避免只看 UI 面板导致误判。

### 🔸 Windows 平台采集与离线分析注意事项
记录 Windows 平台使用 Winscope 时的 adb 路径、浏览器下载、文件命名和大 trace 加载风险。

<!-- outline-end -->

> 本节内容待加工。
