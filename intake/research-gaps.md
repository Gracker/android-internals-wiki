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


## [2026-06-24] Task 2A 知识缺口挖掘 — Round 2（02:04 AM）

### 本轮结论
本轮未发现评分 ≥ 14 的新知识缺口。AIW 已进入高覆盖成熟期（全书 400+ 小节）。

### 已检查但未达阈值（< 14 分）的新方向

| 方向 | 分数 | 判断理由 |
|------|------|----------|
| Android 17 LE Audio / 蓝牙音频性能 | 13 | 素材中等，时效性好（Android 17 新），但读者需求面偏窄（仅影响蓝牙音频配件场景） |
| Android 17 BroadcastQueue 广播分发性能 | 12 | 1.17 IPC 全景部分覆盖；BroadcastQueue 在 Android 14+ 有 modernize 但性能素材不充分 |
| Android 17 屏幕旋转全链路性能 | 12 | 1.24 覆盖 Configuration change；传感器→WM→SF→App 全链路分析有价值但官方素材偏薄 |
| Android 17 Java ClassLoader 运行时加载性能 | 12 | 1.7 ART 编译覆盖；1.22 Verifier Quickening 覆盖；运行时类加载开销有实际影响但缺乏独立素材 |
| Android 17 VpnService / VPN 隧道网络性能 | 11 | 开发者文档覆盖 VPN API；性能开销素材偏理论，缺乏 AOSP 级实测 |
| Android 17 Launcher3 / Quickstep 性能 | 11 | 7.13 SystemUI 覆盖部分；Launcher3 开源但独立于 AOSP platform，素材边界不清 |
| Android 17 CursorWindow / BulkCursor 共享内存机制 | 11 | 10.7/24.2 SQLite/Room 覆盖查询层；CursorWindow 共享内存传输机制是底层细节，素材不足 |
| Android 17 WindowInsetsController 动画性能 | 11 | 2.26 edge-to-edge + 3.12 Predictive Back 覆盖 insets 动画；独立成节素材不够 |
| Android 17 ContentCaptureService 性能影响 | 9 | 边缘系统服务，性能影响面小，开发者文档极少 |
| Android 17 AutofillService 表单填充性能 | 9 | 边缘场景，性能影响有限 |
| Android 17 TextClassifier / Smart Selection 性能 | 9 | ML 推理影响文本选择，但受众面极窄 |
| Android 17 Runtime Resource Overlay (RRO) 性能 | 8 | OEM 专属，与 App 开发者关系小 |

### 已有的覆盖确认
- Part 1（Ch1-6）：系统架构/渲染/输入/内存/调度/存储 — 100+ 小节，核心机制全覆盖
- Part 2（Ch7-12,18）：流畅性/响应/ANR/内存/功耗/网络/渲染管线 — 专题深度充分
- Part 3（Ch13-15,19,27）：工具/方法论/APM/性能工程体系 — 工具链和方法论完整
- Part 4（Ch16-17）：AOSP/OEM — 系统级优化和厂商实践有覆盖
- Part 5（Ch20-26）：应用层优化 — 实战章节覆盖稳定/启动/渲染/内存/IO/功耗/可观测

### 下一步建议
1. 重点转向已有 draft 章节的内容深化（ch27 性能工程体系 6 节有 draft 内容可进一步充实）
2. 关注 Task 2B queue 中的 pending 条目（3.12, 2.29, 4.15, 12.8 等）
3. 下一轮挖掘可关注：Android 17 正式发布后（Platform Stability → AOSP release）可能新增的官方文档
