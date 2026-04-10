---
title: "链路分析方法论"
chapter: "18.20"
status: ready-for-review
applicable_versions: "Android 9 (API 28) - Android 16 (API 36)"
tags: ["方法论", "渲染链路", "Perfetto", "dumpsys", "诊断", "BufferQueue", "性能分析"]
related_chapters: ["2.1", "2.6", "13.5", "15.1"]
created_by: "rendering-pipelines-merge"
created_date: "2026-04-09"
---

<!-- outline-start -->

**锚点（必须覆盖）：**
- Step 1：识别当前场景的渲染模式（哪条链路）
- Step 2：确定 Producer / Consumer / BufferQueue 链路
- Step 3：在 Perfetto 中定位关键 Track 和 Slice
- Step 4：常见瓶颈模式与诊断思路
- 常用 dumpsys 命令速查
- 链路选型决策树

**扩展（可选深入）：**
- 帧率/延迟/功耗三维分析框架
- 跨链路问题的诊断（如 WebView + 主 App 互相影响）
- 章节交叉引用表

<!-- outline-end -->

## 为什么需要链路分析方法论

当用户反馈"App 卡了"，你打开 Perfetto 看到密密麻麻的 Track，第一步不是去逐行看 Slice——而是**先判断这帧走的是哪条链路**。不同的链路有不同的生产者线程、不同的 Buffer 传输机制、不同的同步模型。SurfaceView 的问题看 SurfaceFlinger，TextureView 的问题看 App RenderThread，WebView 的问题可能看 Chromium 的 Compositor Thread。链路判断错了，后续所有的优化方向都是南辕北辙。[已验证: 实践经验]

本章提供一套系统化的链路分析方法论，帮助你在 Perfetto 中快速定位渲染瓶颈。

## Step 1：识别渲染模式

在动手分析之前，先回答一个关键问题：**这个场景走的是哪条链路？**

### 快速判断清单

| 场景 | 典型链路 | 确认方法 |
|:---|:---|:---|
| 普通 RecyclerView 列表 | 18.2 Android View 标准链路 | App 主线程 + RenderThread |
| 地图模块（GLES） | 18.8 OpenGL ES 链路 | 独立 GL Thread |
| 视频播放（全屏） | 18.15 Video Overlay + HWC | SurfaceView + HWC Overlay |
| 视频（内嵌页面） | 18.13 WebView + 18.7 TextureView | 看实现方式 |
| Camera 预览 | 18.14 Camera 管线 | HAL → SurfaceView / TextureView |
| Flutter 应用 | 18.12 Flutter 链路 | Dart Runner + Raster Thread |
| 游戏（Unity/Unreal） | 18.16 游戏引擎链路 | UnityMain/RenderThread |
| 离屏渲染（Android 14+） | 18.17 HardwareBufferRenderer | GPU → AHardwareBuffer |
| PIP / Freeform | 18.18 多窗口渲染 | 多 Layer + Resize 竞态 |
| 高刷屏幕 | 18.19 VRR 管线 | 动态 VSync 周期 |

### dumpsys 快速确认

```bash
# 查看所有 Layer 及其 Composition Type
adb shell dumpsys SurfaceFlinger --list

# 查看特定 Layer 的详细信息
adb shell dumpsys SurfaceFlinger | grep -A 20 "SurfaceView"

# 查看 BufferQueue 状态
adb shell dumpsys SurfaceFlinger --bufferinfo
```

## Step 2：确定 Producer-Consumer 链路

确定链路后，画出 Producer-Consumer 关系：

| 链路 | Producer | Consumer | 中间经过 |
|:---|:---|:---|:---|
| 标准链路 | App UI + RT | SurfaceFlinger | BLASTBufferQueue |
| SurfaceView | 独立线程 | SurfaceFlinger | 独立 BufferQueue |
| TextureView | 独立线程 | App RT → SF | SurfaceTexture |
| WebView GL Functor | Chromium (in RT) | SF (via RT) | 共享 EGLContext |
| Camera | HAL/ISP | SF + MediaCodec + ImageReader | 多 BufferQueue |

**关键问题**：帧数据从 Producer 到 Consumer 经过了几跳？每跳之间有没有多余的拷贝或等待？

## Step 3：Perfetto 关键定位

### 必看的 Track

| Track | 关注内容 |
|:---|:---|
| **App 主线程** | `doFrame` 耗时，Measure/Layout/Draw 分布 |
| **RenderThread** | `DrawFrame` 耗时，`queueBuffer`/`dequeueBuffer` 等待 |
| **SurfaceFlinger** | `setTransactionState`、`latchBuffer`、合成耗时 |
| **VSYNC** | VSync-App 和 VSync-SF 的周期 |
| **GPU** | GPU 任务队列和执行时间 |
| **HWC** | validate 结果（DEVICE/CLIENT） |

### 关键 Slice 速查

| Slice | 含义 | 出了问题说明 |
|:---|:---|:---|
| `doFrame` 超长 | 主线程卡顿 | Measure/Layout/Draw 太重 |
| `DrawFrame` 超长 | RT 渲染慢 | GPU 指令太多或太复杂 |
| `dequeueBuffer` 阻塞 | 没有空闲 Buffer | Consumer 消费太慢 |
| `queueBuffer` 阻塞 | BufferQueue 满了 | SF 还没消费上一帧 |
| `syncFrameState` 阻塞 | RT 忙碌 | UI 等待 RT 完成 |
| `updateTexImage` 阻塞 | GPU 还在画 | acquireFence 未 signal |
| `latchBuffer` 阻塞 | acquireFence 未 signal | GPU 渲染未完成 |
| `Invoke Functor` 超长 | WebView/GL 回调慢 | 网页内容太复杂 |

### SQL 诊断速查

```sql
-- 1. 找最耗时的 doFrame
SELECT ts, dur FROM slice 
WHERE name = 'Choreographer#doFrame' 
ORDER BY dur DESC LIMIT 10;

-- 2. 找 BufferQueue 阻塞
SELECT name, dur, ts FROM slice 
WHERE name IN ('dequeueBuffer', 'queueBuffer') 
AND dur > 5000000
ORDER BY dur DESC;

-- 3. VRR 感知的掉帧检测
INCLUDE PERFETTO MODULE android.frames;
SELECT frame_id, ts, dur, jank_type
FROM android_frames
WHERE jank_type != 'None'
ORDER BY ts DESC LIMIT 20;
```

## Step 4：常见瓶颈模式

### 模式 A：主线程卡顿

**特征**：`doFrame` 超过 16.6ms，Measure/Layout 占大头。
**链路**：标准链路（18.2）。
**诊断**：在主线程 Track 中找耗时最长的方法。
**优化**：减少布局层级、延迟执行、异步布局。

### 模式 B：GPU 过载

**特征**：`DrawFrame` 超长，GPU Track 持续满载。
**链路**：任何涉及 GPU 渲染的链路。
**诊断**：检查 DrawCall 数量、Overdraw、Shader 复杂度。
**优化**：减少 Overdraw、合批 DrawCall、简化 Shader。

### 模式 C：BufferQueue 饥饿

**特征**：`dequeueBuffer` 频繁阻塞。
**链路**：任何使用 BufferQueue 的链路。
**诊断**：Consumer 消费速度跟不上 Producer，或 Buffer 深度不够。
**优化**：增加 Buffer 深度、加速 Consumer、检查 Fence 等待。

### 模式 D：HWC Overlay 失效

**特征**：GPU Track 出现额外的合成任务。
**链路**：本应走 Overlay 的 SurfaceView 回退到 GPU。
**诊断**：`dumpsys SurfaceFlinger` 查看 Composition Type。
**优化**：移除 SurfaceView 的 Alpha/Transform/圆角设置。

### 模式 E：VRR 误判

**特征**：工具报告大量"掉帧"，但视觉上并不卡。
**链路**：VRR 设备（18.19）。
**诊断**：使用 Perfetto `android_frames` 模块而非固定阈值。
**优化**：使用 `setFrameRate()` 明确帧率意图。

## 链路选型决策树

```
需要嵌入复杂 View 层级？
├── 是 → 需要动画/变换/圆角？
│         ├── 是 → TextureView / HardwareBufferRenderer
│         └── 否 → SurfaceView
└── 否 → 内容是视频/游戏/Camera？
          ├── 是 → SurfaceView（性能最优）
          └── 否 → 标准 Android View 链路

是 WebView？
├── 国内 SDK → Custom TextureView 模式
├── 全屏视频 → SV Wrapper 模式
├── 现代设备 → 可能 SurfaceControl 模式
└── 其他 → GL Functor 模式（默认）

是 Flutter？
├── 全屏应用 → SurfaceView render mode
├── 嵌入复杂层级 → TextureView render mode
└── 需要 PlatformView → 注意 HC/TLHC 组合开销
```

## 章节交叉引用表

如果你遇到以下问题，先看对应章节：

| 问题 | 章节 |
|:---|:---|
| RecyclerView 滑动卡顿 | 18.2 + 7.8 |
| SurfaceView 视频黑屏/闪烁 | 18.6 + 18.15 |
| TextureView 功耗高 | 18.7 |
| WebView 页面卡拖慢 App | 18.13 |
| Camera 预览掉帧 | 18.14 |
| Flutter 嵌入原生 View 性能差 | 18.12 |
| 游戏帧率不稳 | 18.16 |
| PIP 窗口 Resize 黑边 | 18.18 |
| VRR 设备误报掉帧 | 18.19 |
| HWC Overlay 失效 | 18.15 |
| 离屏渲染性能差 | 18.17 |

## 与其他章节的关系

- **15.1 性能优化的术、道、器**：方法论的哲学层面
- **13.5 Perfetto 专题解读**：Perfetto 工具的使用技巧
- **18.1 渲染链路分类与选择矩阵**：本章的索引和入口

## 参考资料

- Android 官方文档：Graphics architecture
- Perfetto 官方文档：Trace analysis
- AOSP `frameworks/native/services/surfaceflinger/`
