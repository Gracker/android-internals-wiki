---
title: "DisplayManagerService Display Lifecycle 与拓扑性能"
chapter: "2.30"
status: draft
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
tags: [display, dms, multi-display, foldable, surfaceflinger, syncroot]
related_chapters: ["2.3", "2.6", "2.20", "2.23", "2.28", "18.5"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "DeepResearch素材驱动"
---

# 2.30 DisplayManagerService Display Lifecycle 与拓扑性能

<!-- outline-start -->
## 要点

### 🔹 DisplayManagerService 架构与单锁模型
DMS 的 SyncRoot 全局锁设计：所有 display 状态变更（adapter 注册、display 添加/移除、power state 切换）都在 mSyncRoot 下序列化。单锁模型的性能边界——何时成为瓶颈，何时不是。

### 🔹 DisplayAdapter 体系与 display 发现
LocalDisplayAdapter、VirtualDisplayAdapter、OverlayDisplayAdapter、WifiDisplayAdapter 四条发现链路。DisplayDevice → LogicalDisplay 的映射流程。DISPLAY_DEVICE_EVENT_* 事件投递机制。

### 🔹 LogicalDisplayMapper 与 DisplayGroup/DisplayTopology
物理 display 到逻辑 display 的映射规则。Android 17 新增的 DisplayTopologyCoordinator 如何管理多 display 拓扑关系。Layout（设备状态 → 布局）的驱动机制。setDeviceState 异步落地路径。

### 🔹 DisplayEventReceiver 与 per-display VSync 投递
每个 display 独立的 VSync 事件投递链路。Choreographer 与 display 的绑定关系。Display 切换时 VSync 的过渡行为。

### 🔹 Display Power State 切换性能
DisplayPowerController 的亮度/功耗状态机。shouldDeviceBeWaked/setDisplayState 的异步路径。与 PowerManager.wakeUp/goToSleep 的联动。

### 🔹 多 display 拓扑变更对 SurfaceFlinger 的影响
Display 添加/移除时 SurfaceFlinger layer 树的重建开销。DisplayToken 的创建与释放。hot-plug 事件的端到端延迟。

### 🔹 启动阶段 display 等待
PHASE_LOCKED_BOOT_COMPLETED 阶段 DMS 阻塞等待默认 display 的机制。system_server 启动与 SurfaceFlinger ready 的时序依赖。

## 扩展

### 🔸 虚拟 display 创建/销毁开销
VirtualDisplay 的 SurfaceControl 分配与释放性能。VirtualDisplayAdapter 的 callback 投递模型。

### 🔸 Display rotation/resize 的渲染性能路径
Display.Mode 切换对 BufferQueue、Choreographer、SurfaceFlinger 的影响链。Mode 切换的 frame drop 行为。

### 🔸 折叠屏 hinge state → display topology change
折叠/展开时 DisplayTopologyCoordinator 的拓扑重建流程。DualDisplay → SingleDisplay 过渡的渲染中断风险。

<!-- outline-end -->

> 本节内容待加工。

[结构参考: DeepResearch/2026-06-24-android-17-displaymanagerservice-multi-display-architecture.md]
