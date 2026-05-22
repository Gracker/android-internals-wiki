---
title: "HWC Overlay Plane 与合成降级排查"
chapter: "7.18"
status: draft
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [hwc, surfaceflinger, overlay-plane, jank, perfetto]
related_chapters: ["2.6", "2.15", "2.16", "7.6", "7.15", "14.15", "18.15"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-23"
gap_source: "章节深挖/研究素材/AOSP结构/官方文档"
gap_score: 18
material_count: 4
---

# 7.18 HWC Overlay Plane 与合成降级排查

<!-- outline-start -->
## 要点

### 🔹 问题边界：App 帧正常但显示仍掉帧
说明 HWC Overlay Plane 和 SurfaceFlinger 合成降级适合解释哪类卡顿：App 主线程、RenderThread 看起来没有超时，但 FrameTimeline 或屏幕呈现仍出现 SF missed / DisplayHAL 侧异常。

### 🔹 HWC 合成协商流程
梳理 `validateDisplay()`、`getChangedCompositionTypes()`、`acceptDisplayChanges()`、`presentDisplay()` 的协作顺序，明确 `DEVICE` 与 `CLIENT` composition 的含义和排查价值。

### 🔹 Overlay Plane 能力上限
整理 Plane 数量、像素格式、alpha / blending、旋转缩放、受保护内容、带宽和 vendor policy 对合成类型的影响，避免只按 Layer 数量下结论。

### 🔹 Perfetto 与 dumpsys 证据采集
给出 `android.surfaceflinger.frametimeline`、SurfaceFlinger 进程 slice、Layer trace、Winscope 和 `dumpsys SurfaceFlinger` 的证据组合，说明每类证据能回答的问题。

### 🔹 典型触发场景
围绕视频通话、相机预览 + UI 浮层、播放器字幕/弹幕、多窗口、系统栏叠加等场景，拆出 Layer 数量、Layer 属性和刷新率/分辨率变量。

### 🔹 优化动作与回归验证
整理减少独立 Layer、合并 overlay、调整 SurfaceView Z-order、降低缩放/旋转组合、分设备灰度和同机 trace 对比的验证方法。

## 扩展

### 🔸 Qualcomm / MediaTek / Pixel HWC 策略差异
记录公开资料能确认的边界；厂商私有策略必须标注为待验证或实机证据。

### 🔸 与 18.15 视频叠加和 HWC 的交叉引用
本节只写排查和治理动作，HWC / 视频叠加原理详见 18.15 节，SurfaceFlinger 合成机制详见 2.6 节。

### 🔸 线上指标设计
探索是否能把 CLIENT composition 比例、SF missed frame、设备型号和场景标签纳入线上问题分群。

<!-- outline-end -->

> 本节内容待加工。
