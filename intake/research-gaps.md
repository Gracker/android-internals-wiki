## [2026-06-23] 18.14 Camera 渲染管线 — 知识盲区

### 盲区描述
Camera HAL buffer management 与 BufferQueue 协作的内存模型：GraphicBuffer 在 HAL 和 Framework 间的所有权转移机制、内存分配策略、同步原语使用，以及在不同 Stream Use Case 下的内存优化策略。

### 重要程度
高，涉及性能调优关键点

### 建议研究方向
- 研究 AOSP Camera HAL3 中 GraphicBuffer 的生命周期管理
- 分析 BufferQueue 与 HAL buffer 的同步机制
- 探究不同 Stream Use Case 对内存占用的影响
- 研究 ZSL 模式下的内存拷贝优化策略

### 关联章节
2.13, 2.15, 14.9, 18.6

---

## [2026-06-23] 18.14 Camera 渲染管线 — 知识盲区

### 盲区描述
CameraX ZSL 与底层 HAL reprocessing 的映射关系：CameraX ring buffer 如何与 HAL reprocessing request 对应、不同设备间的 HAL 能力差异对 ZSL 实现的影响。

### 重要程度
中，影响库层使用

### 建议研究方向
- 研究 CameraX ZSL 实现与 HAL reprocessing 的映射关系
- 分析不同设备 HAL 能力对 ZSL 策略的影响
- 研究 CameraX 在不同 Android 版本中的兼容性处理

### 关联章节
2.13, 14.9, 18.6

---

## [2026-06-23] 26.12 Android 版本化线上诊断能力 — 知识盲区

### 盲区描述
StatsD 原子数据与诊断能力的集成关系：StatsD 原子计数器与 ApplicationExitInfo 状态的关联分析、系统级诊断的原子数据采集机制。

### 重要程度
高，影响系统级诊断完整性

### 建议研究方向
- 研究 Android StatsD 原子计数器的采集机制
- 分析 ApplicationExitInfo 与 StatsD 数据的集成关系
- 探究系统级诊断能力的原子数据验证方法

### 关联章节
20.7, 8.10, 12.5
---

## [2026-06-24] Task 2A 知识缺口挖掘 — 已检查方向

### 已录入新章节
- **3.12 Predictive Back 系统架构与动画管线性能** (Score: 16/20) — 22.13 覆盖应用侧动画，系统侧 InputDispatcher→WMS→SF 管线未覆盖
- **2.29 TaskSnapshot 系统架构与 Recents 渲染性能** (Score: 14/20) — AOSP TaskSnapshotController/TaskSnapshotPersister 源码驱动

### 已检查但未达阈值（< 14 分）的方向
- Configuration Change 全链路性能（1.24 已充分覆盖 ResourcesManager + Activity recreation）— Score: 12
- NotificationManagerService 渲染管线（8.14 已覆盖 NMS 入队/速率限制/分组/heads-up）— Score: 10
- DisplayManagerService 多显示器管理（2.20 部分覆盖多窗口渲染，DMS 专属内容素材偏薄）— Score: 12
- Treble HAL 架构与性能边界（HIDL/AIDL IPC 开销有文档但缺乏性能实测素材）— Score: 12
- InputMethodService 渲染架构（3.11 已覆盖 IMMS 架构和 IME 性能）— Score: 11
- Companion Device Manager / Cross-Device 性能（边缘场景，素材不足）— Score: 12
- Live Wallpaper / WallpaperManagerService 性能（素材严重不足）— Score: 9
