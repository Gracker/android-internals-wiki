---
title: "TaskSnapshot 系统架构与 Recents 渲染性能"
chapter: "2.29"
status: ready-for-review
drafted_date: "2026-06-24"
applicable_versions: "Android 9 (API 28) - Android 17 (API 37)"
last_verified: "2026-06-24"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotController.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotPersister.java"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/TaskSnapshot.java"
  - type: aosp
    path: "frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/startingsurface/"
  - type: official
    path: "developer.android.com/reference/android/view/SurfaceControl"
tags: [tasksnapshot, recents, overview, rendering, memory, surfaceflinger]
related_chapters: ["2.6", "2.12", "2.13", "2.15", "4.1", "8.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-24"
gap_source: "AOSP结构+章节深挖"
gap_score: 14
---

# 2.29 TaskSnapshot 系统架构与 Recents 渲染性能

Android 9 引入 TaskSnapshot 机制，让系统在 Task 切到后台时保存一帧像素快照，后续在 Recents/Overview、StartingWindow、App 切换动画中使用这帧快照代替实际 Surface 渲染。这减少了动画过程中的进程唤醒和 GPU 绘制开销，但也引入了内存占用、快照新鲜度、折叠屏分辨率不匹配等问题。

本节覆盖 TaskSnapshot 的触发时机、内存模型、持久化路径、Recents 渲染管线中的使用方式、低内存降级、折叠屏复杂度，以及性能观测方法。

## TaskSnapshot 的触发时机与捕获机制

### 触发事件

TaskSnapshotController（`frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotController.java`）在以下系统事件中触发快照捕获：

1. **Task 可见性变化为 false**：用户离开当前 Task（按 Home、切换到另一个 Task），WMS 的 `setTaskVisibility()` 路径调用 `TaskSnapshotController#snapshotTask()`。
2. **App Transition**：`AppTransitionController` 在过渡动画启动前，对即将不可见的 Task 截取快照。
3. **进程冻结前**：Cached App Freezer 在冻结进程前确认 snapshot 有效，冻结后 UI 不再更新，snapshot 作为该 Task 的视觉代表。

### 捕获路径

快照捕获的核心调用链：

```
TaskSnapshotController.snapshotTask(Task)
  → SurfaceControl.captureLayersExcluding(layer, excludeLayer, ...)
    → SurfaceFlinger::captureLayersImpl()
      → 读取 GraphicBuffer 内容
    → 返回 HardwareBuffer
  → 创建 TaskSnapshot(HardwareBuffer, scale, insets)
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotController.java]

`SurfaceControl.captureLayersExcluding()` 是 Android 10（API 29）引入的 API，它让 WMS 在 SurfaceFlinger 的下一帧合成前，同步读取指定 layer 子树的像素内容。这个调用持有 `mGlobalLock`（WMS 全局锁），执行时间取决于 layer 层级深度和分辨率。

Android 9 使用 `SurfaceControl.screenshot()` 截取全屏像素，再裁剪到 Task 区域。Android 10+ 改用 `captureLayersExcluding()`，只读取目标 Task 的 layer 树，避免全屏截取的开销。

### HardwareBuffer 的性能收益

Android 10+ 的 TaskSnapshot 使用 `HardwareBuffer` 包装捕获的 `GraphicBuffer`。与 Android 9 的 `Bitmap` 方案相比：

| 方案 | 内存位置 | GPU 直接采样 | 创建开销 |
|------|---------|-------------|---------|
| Bitmap (Android 9) | Java 堆 / ashmem | 需上传纹理 | 高 |
| HardwareBuffer (Android 10+) | Gralloc DMA-buf | 直接作为纹理源 | 低 |

HardwareBuffer 可以直接传给 GPU 作为 samplerExternalOES 纹理，省掉了 Bitmap → texture 的上传步骤。在 Recents 动画中，snapshot 要作为 texture layer 参与合成，直接采样 DMA-buf 比从 ashmem 上传快得多。

### snapshot 捕获与 Activity onPause 的时序

```
1. InputEvent → Home key
2. ATMS.setTaskVisibility(task, false)
3. WMS 准备 App Transition
4. TaskSnapshotController.snapshotTask(task)  ← 同步捕获快照
5. App Transition 动画启动（使用 snapshot 作为 source）
6. Activity.onPause() 回调到 App
7. Task 进入后台 / 冻结
```

snapshot 捕获在 `onPause()` 之前执行。这样 Recents 动画启动时已经有了快照可用，不会出现空白帧。

## Snapshot 内存模型与压力管理

### 单张快照的内存占用

TaskSnapshot 的内存占用由分辨率和像素格式决定。`captureLayersExcluding()` 默认使用 `PIXEL_FORMAT_RGBA_8888`（4 bytes/pixel）。

典型设备上的单张快照大小：

| 分辨率 | 像素数 | RGBA_8888 大小 |
|--------|--------|---------------|
| 1080×2400 | 2,592,000 | ~9.9 MB |
| 1440×3120 | 4,492,800 | ~17.2 MB |
| 720×1600 (低 RAM) | 1,152,000 | ~4.4 MB |

### 多任务场景的总占用

用户后台任务数量没有硬上限（由 lmkd 按 cached memory 阈值控制）。假设 10 个后台 Task，1080p 设备的 snapshot 总内存占用约 99 MB。这部分内存属于 Gralloc 分配的 DMA-buf，不计入 Java 堆，但计入系统整体图形内存。

查看系统图形内存总量的方法：

```bash
adb shell dumpsys SurfaceFlinger | grep -A5 "Total memory"
adb shell dumpsys gfxinfo | grep "Total GPU memory"
```

### 缓存策略与 LRU 淘汰

TaskSnapshotController 内部维护 `mNestedTaskSnapshotCache`（Android 12+ 拆分为 `SnapshotCache` 和 `mTaskIdToSnapshotCache`），按 LRU 策略管理。当系统内存压力升高（`ActivityManager.onTrimMemory()` 回调到 `TRIM_MEMORY_RUNNING_LOW` 或更高级别），WMS 释放非当前可见 Task 的 in-memory snapshot HardwareBuffer，只保留磁盘上的持久化文件。

lmkd 的 cached memory 阈值判定不看 snapshot 占用的 DMA-buf 内存——DMA-buf 属于系统级图形内存，不在 lmkd 的 memcg 统计范围内。snapshot 大量占用 DMA-buf 可能导致 Gralloc 内存压力，表现为新 buffer 分配失败或 `GPU out of memory`，但不直接触发 lmkd kill。

## Snapshot 持久化与重启后恢复

### TaskSnapshotPersister 的磁盘写入

TaskSnapshotPersister（`frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotPersister.java`）负责把 in-memory snapshot 异步写入磁盘。

- **存储路径**：`/data/system/app_snaps/`
- **文件命名**：`<task_id>_<user_id>.jpg`（JPEG 格式）和 `<task_id>_<user_id>_proto.pb`（元数据，包含 scale、insets 等信息）
- **写入时机**：在 snapshot 创建后通过 `mBgHandler.post()` 投递到后台 Handler 线程，不阻塞 WM 主线程
- **JPEG 质量**：默认 quality = 100（无损压缩优先视觉质量，牺牲磁盘空间）

JPEG 格式选择是磁盘占用和加载速度的权衡。RGBA_8888 原始格式写入磁盘对于 1080p 快照约 10 MB/张，JPEG 100 quality 压缩后通常 500 KB - 2 MB。加载时 JPEG 解码延迟约 10-30 ms，由 `TaskSnapshotLoader` 在后台线程执行。

### 设备重启后的恢复路径

设备重启后，WMS 初始化阶段通过 `TaskSnapshotPersister.reset()` 清空 in-memory cache。当用户打开 Recents 或点击最近任务时，`SnapshotController.getSnapshot(taskId)` 发现内存缓存未命中，从磁盘加载：

```
SnapshotController.getSnapshot(taskId)
  → SnapshotCache.getSnapshot(taskId)  // miss
  → TaskSnapshotPersister.getSnapshot(taskId)
    → TaskSnapshotLoader.loadTaskSnapshot()
      → JPEG 解码 → HardwareBuffer
    → 返回 TaskSnapshot
```

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotPersister.java]

加载是按需的——不是重启时一次性加载所有 snapshot，而是用户触发时才加载对应的那个。这避免了重启后大量 JPEG 解码导致的 I/O 峰值。

### Low-RAM 设备的持久化禁用

`ActivityManager.isLowRamDevice()` 返回 true 的设备（≤ 4GB RAM，`ro.config.low_ram` 属性控制），TaskSnapshotPersister 会根据 `frameworks/base/core/res/res/values/config.xml` 中的 `config_snapshotPersistable` 配置决定是否禁用持久化。低 RAM 设备通常禁用持久化，只在内存中缓存少量 snapshot，设备重启后 Recents 不显示缩略图。

[待验证: 低 RAM 设备 config_snapshotPersistable 默认值可能因 OEM 配置而异]

## Recents/Overview 渲染管线中的 Snapshot 使用

### RecentsAnimationController 的显示策略

RecentsAnimationController（WM Shell 侧，`frameworks/base/libs/WindowManager/Shell/src/com/android/wm/shell/recents/`）在 Overview 动画中区分两种模式：

1. **Live tile 模式**：Task 对应的 App 进程仍然存活，实际 Surface 作为动画源。用户上滑时看到的是 App 的实时画面在缩小。
2. **Snapshot 模式**：App 进程已被杀或冻结，使用 TaskSnapshot 作为动画源。

### 从 Snapshot 到 Live Render 的切换

当用户从 Recents 点击一个 Task 返回前台：

```
1. RecentsAnimation 启动 → 使用 snapshot 作为 source layer
2. WMS 准备恢复 Task 可见性
3. 如果进程存活：
   a. 解冻进程（如果在冻结状态）
   b. 等待 App 下一帧绘制完成
   c. 切换 source：snapshot layer → App 实际 SurfaceControl
   d. 移除 snapshot layer
4. 如果进程已被杀：
   a. 重新启动进程（冷启动路径）
   b. Snapshot 作为 starting surface 持续显示
   c. App 主窗口首帧完成后移除 snapshot
```

步骤 3c 是关键切换点。如果 App 的第一帧在动画中途完成，会出现 snapshot → live surface 的视觉跳变。`RecentsAnimationController` 通过设置 `Leash` layer 的 z-order 和 alpha 渐变来掩盖这个跳变。

### SurfaceFlinger 层面的合成路径

snapshot 作为 `SurfaceControl` layer 参与合成时，有两种路径：

- **BufferStateLayer**（Android 10+ 默认）：snapshot 的 HardwareBuffer 通过 `SurfaceControl.setBuffer()` 设置为 layer 的 buffer，走标准合成路径。HWC 可以直接将这个 buffer 作为 DEVICE composition layer。
- **BufferQueueLayer**（Android 9 兼容）：snapshot 通过 BufferQueue 以 texture 形式提交，走 CLIENT composition 路径（GPU 合成）。

BufferStateLayer 路径让 HWC 有机会直接合成 snapshot buffer，不需要 GPU 参与。这对 Recents 动画的帧率稳定性有直接帮助——GPU 不需要处理 snapshot 的纹理采样。

### 缩放渲染的颜色空间

snapshot 捕获时的颜色空间由 `SurfaceFlinger::captureLayersImpl()` 按当前 display 的 color mode 决定。如果 display 处于 Wide Color Gamut（WCG）模式，snapshot 使用 `DATASPACE_DISPLAY_P3`。Recents 动画中 snapshot 被缩放显示时，如果目标 layer 的颜色空间与 snapshot 不一致，GPU 需要做颜色空间转换（color transform matrix），这会增加 shader 处理量。大部分场景下这种开销可以忽略。

## 低内存设备与极端场景的 Snapshot 降级

### 低 RAM 设备策略

`ro.config.low_ram=true` 的设备（通常 ≤ 4GB RAM）对 TaskSnapshot 做以下降级：

| 维度 | 普通设备 | Low-RAM 设备 |
|------|---------|-------------|
| 捕获分辨率 | Task 原始分辨率 | 按 `config_lowRamTaskSnapshotScale`（通常 0.5）缩放 |
| 持久化 | 启用 | 通常禁用 |
| 缓存数量 | 无硬上限（由 LRU 管理） | 限制到最近 3-5 个 Task |
| 像素格式 | RGBA_8888 | 可能降级到 RGB_565（节省 50% 内存） |

分辨率缩放通过 `TaskSnapshotController` 中的 scale 参数传给 `captureLayersExcluding()`，在 SurfaceFlinger 捕获阶段直接按 scale 因子降采样，不需要先捕获全分辨率再缩放。

### 进程被杀后的 snapshot 保留

当后台 App 进程被 lmkd 杀掉后，TaskSnapshotController 不会主动清除该 Task 的 snapshot。用户在 Recents 中看到的是这个 Task 被杀前的最后一帧画面。点击恢复时走冷启动路径。

这是设计意图而非 bug：保留 snapshot 让用户感知到"任务还在那里"，减少重新启动的视觉割裂。如果 snapshot 也被清除，Recents 会显示空白缩略图，用户不知道这个 Task 是什么。

### 冻结进程的 snapshot 有效性

Cached App Freezer 冻结进程后，进程的 Surface 不再更新（冻结期间 `queueBuffer` 被 blocked）。snapshot 在冻结前已经捕获，因此 snapshot 内容和冻结前最后一帧一致。解冻后 App 恢复绘制，snapshot 自动失效——下一次 Task 不可见时重新捕获。

如果冻结期间 display 配置发生变化（如折叠屏展开），snapshot 的分辨率可能与新 display 不匹配。`TaskSnapshotController` 在 `handleDisplayChange` 路径中会对受影响的 Task 重新捕获。

## 折叠屏与多显示器的 Snapshot 复杂度

### 折叠态 ↔ 展开态的分辨率不匹配

折叠屏设备从内屏（展开态，如 2200×2480）折叠到外屏（折叠态，如 1080×2480）时，snapshot 是在折叠前以展开态分辨率捕获的。Recents 在折叠态分辨率下渲染这个 snapshot，需要缩放和裁剪。

处理路径：

1. `DisplayChangeController` 检测到折叠事件
2. 通知 `TaskSnapshotController.snapshotTask()` 对所有可见 Task 重新捕获
3. 新 snapshot 使用折叠后的 display 分辨率
4. 在重新捕获完成前，Recents 使用旧 snapshot 做临时显示（会短暂出现拉伸/裁剪）

Android 12+ 的 ` WindowManager` 增加了 display change 期间的 snapshot 预捕获机制，在过渡动画开始前异步触发一次新分辨率快照，缩短不匹配窗口期。

[已验证: AOSP android-17.0.0_r1, frameworks/base/services/core/java/com/android/server/wm/TaskSnapshotController.java — handleDisplayChange / snapshotBeforeDisplayChange 路径]

### 多显示器场景

每个 Display 有独立的 Task 列表。TaskSnapshot 按 Task ID 缓存，与 Display 无关。但一个 Task 的窗口可能跨多个 Display（Android 10+ 的 multi-display 模式），snapshot 只捕获 Task 的主 Display 区域。

Android 14 对外部显示器的 Task 做了改进：secondary display 上的 Task 可以独立捕获 snapshot，不再强制使用 primary display 的截图。`TaskSnapshotController` 通过 `Task.getDisplayContent()` 获取 Task 所在的 `DisplayContent`，按该 display 的 layer 树执行捕获。

## TaskSnapshot 性能观测方法

### dumpsys activity tasks

```bash
adb shell dumpsys activity tasks
```

输出中与 snapshot 相关的字段：

```
* Task{#123 type=standard ...)
  - snapshots: scale=1.0
  - last snapshot: 1080x2400 HardwareBuffer
```

`scale=1.0` 表示全分辨率捕获（低 RAM 设备显示 0.5）。`last snapshot` 显示最近一次捕获的分辨率和 buffer 类型。

### Perfetto 中的 snapshot trace

TaskSnapshot 捕获在 Perfetto 中有对应的 trace slice：

| Trace slice | 来源 | 含义 |
|-------------|------|------|
| `SurfaceFlinger::captureLayers` | SurfaceFlinger | 实际像素捕获的执行时间 |
| `TaskSnapshotController::snapshotTask` | WMS (system_server) | WMS 侧的 snapshot 调度时间 |
| `TaskSnapshotPersister::persistTaskSnapshot` | WMS 后台线程 | 磁盘写入耗时 |

Perfetto SQL 查询 snapshot 捕获延迟：

```sql
-- 查找 captureLayers 耗时分布
SELECT
  name,
  EXTRACT_ARG(dur, "dur") / 1e6 AS duration_ms
FROM slice
WHERE name LIKE "SurfaceFlinger::captureLayers%"
  AND ts > :start_ts
ORDER BY duration_ms DESC
LIMIT 20;
```

典型值：1080p 单 Task 约 5-15 ms，1440p 约 10-25 ms。超过 30 ms 说明可能存在 layer 层级过深或 display 处于高负载状态。

### dumpsys SurfaceFlinger 中识别 snapshot layer

```bash
adb shell dumpsys SurfaceFlinger --list | grep -i snapshot
```

snapshot layer 通常以 `Snapshot` 或 `StartingSurface` 前缀出现。在 layer 树中：

```
- Display 0
  - RecentsAnimationHost
    - TaskSnapshot#123        ← snapshot layer
      - buffer: 1080x2400 RGBA_8888
```

snapshot layer 的 buffer 属性显示了捕获时的分辨率和像素格式。

## 扩展

### TaskSnapshot 与 Activity Transition 动画的协同

Activity 之间切换（如从 Activity A 启动 Activity B）时，如果两个 Activity 属于同一 Task，不触发 Task 级别的 snapshot。Activity Transition 使用 `Transition` API（Android 5.0+）或 `ActivityOptions.makeSceneTransitionAnimation()` 在 App 进程内完成动画。

Task 级别的 snapshot 只在 Task 不可见时触发。Activity 级别的过渡不涉及 TaskSnapshot。

### Snapshot 压缩与质量权衡

截至 Android 17，TaskSnapshot 在内存中始终使用未压缩的 RGBA_8888 HardwareBuffer。内存中的 snapshot 没有压缩，因为 GPU 采样需要原始像素。

磁盘持久化使用 JPEG quality=100。降低 JPEG quality 可以减少磁盘占用（quality=85 比 quality=100 约节省 40% 空间），但会增加解码延迟和图像质量损失。目前没有系统级配置让 OEM 调整这个 quality 值。

[待验证: Android 17 是否有新的 in-memory snapshot 压缩方案提案]

### OEM 自定义 Recents 与 TaskSnapshot 的关系

OEM 自研 Launcher（如 MIUI Launcher、One UI Home）如果使用系统的 `RecentsAnimationController` 和 `TaskView`，会自动使用 TaskSnapshot。如果 OEM 完全自研 Recents 实现，不走 `RecentsAnimationController`，则需要自行通过 `ActivityTaskManager.getTaskSnapshot()` API（`@hide`，SystemUI 可用）获取快照，或者自行截图。

兼容性边界：OEM 自定义 Recents 如果绕过系统 snapshot 机制自行截图，可能导致重复截图（系统一次 + OEM 一次），增加内存和 CPU 开销。`TaskSnapshotController` 提供了 `setSnapshotEnabled(taskId, false)` 让 OEM 在特定 Task 上禁用系统 snapshot。

