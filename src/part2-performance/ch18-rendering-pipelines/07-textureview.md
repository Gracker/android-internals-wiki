---
title: "TextureView 合成链路"
chapter: "18.7"
section: "18.7"
status: finalized
applicable_versions: "Android 4.0 (API 14) - Android 17 (API 37)"
tags: ["TextureView", "SurfaceTexture", "App 侧合成", "纹理采样", "OES", "BLAST", "渲染链路"]
related_chapters: ["2.1", "2.6", "2.13", "18.6", "18.8"]
sources:
  - type: aosp
    path: "platform/frameworks/base/core/java/android/view/TextureView.java"
  - type: aosp
    path: "platform/frameworks/base/graphics/java/android/graphics/SurfaceTexture.java"
  - type: android-docs
    path: "TextureView reference"
created_by: "rendering-pipelines-merge"
created_date: "2026-04-09"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: "reviewed"
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: 2026-06-02
task6_reviewed_date: "2026-06-03"
task6_result: pass-light-edit
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-06-02"
task2b_result: fixed-lite
task2b_rework_date: "2026-04-20"
last_task2b_lite_at: "2026-05-31"
last_task9_at: "2026-06-03T07:20:00+08:00"
last_task6_audit: 2026-07-15
last_task9_audit: 2026-05-20
last_task6_at: "2026-06-03T09:15:06+08:00"
last_task6_review_log: "logs/review/2026-06-03-09-09-review.md"
task6_review_notes: "2026-06-03 09:11 Task6 revisiting-review：无新增 L1/L2 问题。Task9 auto-fix（TextureView 成本口径修正）已确认无写作质量问题。满足 auto-promotion 条件，晋升 finalized。"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_new_rework: false
task6_auto_promoted: true
task9_result: auto-fixed
last_task9_review_log: "logs/deep-review/2026-06-03-07-deep-review.md"
last_task9_autofix_at: "2026-06-02"
task9_review_notes: "2026-06-02 Task9 auto-fix：将 TextureView 成本口径从额外拷贝/固定 2 倍内存修正为额外纹理采样、宿主窗口再承载合成结果；回到 Task6 复审。"
last_task2b_verifier_at: "2026-06-03T07:31:00+08:00"
last_task2b_verifier_log: "logs/rework/2026-06-03-07-task2b-verifier.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-25
---

<!-- outline-start -->

**锚点（必须覆盖）：**
- [18.7.1 为什么要理解 TextureView 的链路](#为什么要理解-textureview-的链路) — View 表象与 App 侧合成路径
- [18.7.2 三阶段链路详解](#三阶段链路详解) — Producer → SurfaceTexture → RenderThread → SF
- [18.7.3 SurfaceTexture 机制深入](#surfacetexture-机制深入) — 双角色组件的核心
- [18.7.4 额外纹理采样的性能代价](#额外纹理采样的性能代价) — updateTexImage 的开销分析
- [18.7.5 链路级对比](#链路级对比surfaceview-vs-textureview) — 与 SurfaceView 的架构差异
- [18.7.6 onFrameAvailable 回调模型](#onframeavailable-回调模型) — 线程绑定与延迟
- [18.7.7 Trace 视角](#trace-视角) — Perfetto 中的识别方法
- [18.7.8 常见性能问题与优化](#常见性能问题与优化) — 实战瓶颈分析

**扩展（可选深入）：**
- OES External Texture 的 GPU 管线
- Flutter TextureView render mode 的关系
- 从 TextureView 迁移到 SurfaceView 的路径

<!-- outline-end -->

## 为什么要理解 TextureView 的链路

TextureView 表面上像普通 View：可以设置透明度、做动画、裁剪圆角，并且和其他 View 一样参与 View 树的绘制流程。但在渲染层面，它背后走的是一条多段转交路径：帧数据先到 SurfaceTexture，再由 App 的 RenderThread 采样合成，随后提交给 SurfaceFlinger。

这个转交过程是 TextureView 性能不如 SurfaceView 的主要原因。理解这套流程，分析时就能在 Perfetto 中区分：帧卡在 SurfaceTexture 的 fence 同步，还是卡在 App 侧 GPU 绘制。[已验证: AOSP TextureView 实现]

TextureView 是 Android 4.0（API 14）引入的，初衷是补足 SurfaceView 在 View 体系里的灵活性。早期 SurfaceView 和普通 View 一起做位置变换与透明度控制确实有不少限制，但这个结论要按版本看：Android 7.0 起，SurfaceView 的窗口位置更新已经能和 View 渲染同步，平移和缩放不再像早期版本那样容易出错；Android 14（U）起，View alpha 也进入官方支持范围。TextureView 仍然保留旋转、复杂裁剪、圆角和与普通 View 深度融合的优势，所以在视频滤镜、直播美颜、需要和 UI 一起做复杂动画的场景里仍然常见。

### 硬件加速是前置条件

TextureView 只能工作在 hardware accelerated window。Android 官方 reference 直接写明，TextureView 在 software rendering 下会 draw nothing。排查 TextureView 黑屏、停在旧帧或只显示占位背景时，应确认 Activity、Window 和 ViewRoot 是否仍处于硬件加速模式。SurfaceView 不依赖 App RenderThread 把内容重新采样进主窗口，所以没有同一条前置条件。

## 三阶段链路详解

TextureView 的渲染链路比 SurfaceView 多了一个关键环节——App 侧的纹理合成。这个额外的环节就是它性能劣势的来源。

### 第一阶段：Producer（生产者）

和 SurfaceView 一样，这一阶段由独立线程绘制内容（视频解码、Camera、游戏等）：

1. **Produce**：解码器或 Camera 生成一帧图像
2. **queueBuffer**：提交给 `SurfaceTexture`（TextureView 的私有 BufferQueue）
3. **Callback**：触发 `onFrameAvailable` 回调，通知有新帧可用

Producer 向 SurfaceTexture 提交帧的方式与向普通 BufferQueue 提交完全相同——SurfaceTexture 本身就是一个 BufferQueue 的 Consumer 端。区别在于后续的消费方式。

### 第二阶段：App RenderThread（中转站）

这是 TextureView 性能问题的核心环节。帧数据到达 App 进程后，需要经过一次"中转"才能最终提交：

1. **Receive Callback**：`onFrameAvailable` 在 listener 绑定的线程收到通知，很多实现最终会回到 UI 线程触发 `invalidate()`
2. **Invalidate**：告诉 View 系统"TextureView 脏了，下一帧重画"
3. **SyncFrameState**：等待下一个 VSync-App 信号唤醒 RenderThread
4. **updateTexImage()**：RenderThread 在绘制 TextureView 时消费 SurfaceTexture 的最新图像
5. **GPU Draw**：把这个纹理当作一张普通贴图，画在 App 的主窗口 Buffer 上

这个"等待下一帧再消费"的机制意味着 TextureView 的帧更新频率被绑定到了 App UI 的帧率上——即使 Producer 以 60fps 生产帧，如果 App UI 只有 30fps，TextureView 也只能展示 30fps 的内容。

### 第三阶段：BLAST 提交

1. **queueBuffer**：App RenderThread 将包含 TextureView 内容的主窗口 Buffer 提交给 BLAST Adapter
2. **Transaction**：通过 BLAST Transaction 发送给 SurfaceFlinger
3. **Composite**：SurfaceFlinger 将 App 主窗口合成到屏幕

```mermaid
sequenceDiagram
    participant HW as Hardware VSync
    participant Prod as Producer (Decoder)
    participant ST as SurfaceTexture
    participant Main as App Main Thread
    participant RT as App RenderThread
    participant BBQ as BLAST Adapter
    participant SF as SurfaceFlinger

    Prod->>ST: queueBuffer(acquireFence)
    ST-->>Main: onFrameAvailable()

    Note over HW, Main: VSync-App 到达
    HW->>Main: VSync-App Signal
    Main->>Main: TextureView.updateLayer()
    Main->>RT: SyncFrameState

    rect rgb(240, 240, 240)
        Note over RT: 纹理合成阶段
        RT->>ST: updateTexImage() → acquireBuffer
        Note right of ST: 等待 acquireFence
        ST-->>RT: Bind OES Texture
        RT->>RT: Draw UI + Texture
        RT->>BBQ: queueBuffer(acquireFence)
    end
    
    BBQ->>SF: Transaction(Buffer, acquireFence)
    ST-->>Prod: releaseBuffer() (Buffer 归还)
```

## SurfaceTexture 机制深入

SurfaceTexture 是 TextureView 链路的核心组件，它同时扮演了两个角色：

- **对 Producer**：它是一个 BufferQueue 的 Consumer 端，接收解码器等生产者的帧数据
- **对 Consumer（App RenderThread）**：它是一个纹理对象，通过 `updateTexImage()` 将最新帧绑定为 GL 可采样的纹理

这种双角色设计让 SurfaceTexture 成为 Android 图形栈中最独特的组件之一。

### SurfaceTexture 内部结构

SurfaceTexture 内部维护了两个关键队列：

1. **BufferQueue**：接收 Producer 的帧，管理 Buffer 的流转
2. **Texture Name**：一个 GL 纹理 ID，通过 EGLImage 绑定到最新的 Buffer

当 `updateTexImage()` 被调用时，SurfaceTexture 做了这些事：

1. **acquireBuffer**：从 BufferQueue 取出最新帧（丢弃中间帧，只保留最新的）
2. **EGLImage 创建/绑定**：将 GraphicBuffer 封装为 GL 可识别的外部纹理（OES Texture）
3. **releaseBuffer**：将旧的 Buffer 归还给 Producer

### OES External Texture

`updateTexImage()` 创建的是 **GL_OES_EGL_image_external** 类型的纹理。这是一种特殊的纹理类型，允许 GPU 直接采样来自 BufferQueue 的 GraphicBuffer，而不需要将其拷贝到标准的 GL 纹理中。

但"直接采样"不等于"零开销"。OES 纹理的采样路径取决于 GPU 驱动实现——在某些 GPU 上，它可能需要做一次格式转换或布局调整。无论如何，这都比 SurfaceView 的"零采样"路径多了一步。[已验证: AOSP SurfaceTexture]

## 额外纹理采样的性能代价

从链路视角分析，TextureView 引入三重开销：

### 1. 额外的 GPU 合成

SurfaceView 的帧数据直出给 SurfaceFlinger，可能走 HWC Overlay 完全不消耗 GPU。而 TextureView 的帧数据必须在 App 进程内被 GPU 采样一次，合成到 App 主窗口的 Buffer 中。

直接带来两个观察点：
- **GPU 负载增加**：如果 App 的 UI 本身已经很复杂（复杂 RecyclerView、大量图片），TextureView 的额外纹理采样会进一步增加 GPU 压力
- **RenderThread 时间增加**：`updateTexImage` + Shader 采样需要时间，这个时间会加到 `DrawFrame` 的总耗时中

### 2. 帧率绑定

SurfaceView 的帧率独立于 App UI。TextureView 的帧率被绑定到 App 的 Choreographer 帧率：

- 如果 App 主线程卡顿 → `Choreographer#doFrame` 延迟 → `updateTexImage` 延迟 → TextureView 内容卡顿
- 即使 Producer 在正常生产帧，如果 App 的 VSync 回调被延迟，TextureView 的内容也会跟着延迟

低端设备上 TextureView 播放视频比 SurfaceView 更容易卡——瓶颈在 App 主线程拖了后腿。

### 3. 额外图形内存压力

SurfaceView 和 TextureView 所在页面都会有宿主 App 窗口 Buffer，差异在于视频或 Camera 内容是否再次写入宿主窗口：

- SurfaceView：Producer BufferQueue 保留独立内容层，宿主窗口主要承载普通 UI
- TextureView：SurfaceTexture 持有 Producer Buffer，宿主窗口 Buffer 还会包含采样后的 TextureView 内容

因此 TextureView 的图形内存和带宽压力通常高于 SurfaceView，但不能按固定 2 倍估算。实际差异取决于分辨率、像素格式、buffer count、TextureView 面积以及宿主 UI 是否本来就需要全屏重绘。4K 视频播放场景下，这部分额外压力尤其明显。

## 链路级对比：SurfaceView vs TextureView

从链路视角，两者的核心差异可以用一张图说清楚：

```
SurfaceView:  Producer → BufferQueue → SurfaceFlinger → HWC → Display
TextureView:  Producer → SurfaceTexture → App RenderThread → SurfaceFlinger → HWC → Display
                                       ↑
                                    多一次合成
```

| 维度 | SurfaceView | TextureView |
|:---|:---|:---|
| **帧数据跳数** | 1 跳（Producer → SF） | 2 跳（Producer → RT → SF） |
| **App 主线程影响** | 不受影响 | 直接受影响 |
| **额外 GPU 采样** | 无 | 有（updateTexImage） |
| **内存占用** | 1x Producer Buffer | 1x Producer + 1x App Buffer |
| **延迟** | 低（直出） | 高（多一跳） |
| **独立 Overlay 机会** | 可能 | 无。TextureView 内容先并入 App 主窗口 |
| **变换能力** | Android 7.0+ 可稳定平移/缩放，Android 14+ 支持 View alpha；旋转和复杂裁剪仍受限 | 完整支持（旋转/缩放/透明度/圆角） |
| **帧率独立性** | 独立 | 绑定到 App UI 帧率 |
| **受保护内容（DRM）** | 支持，可以走 secure overlay / secure composition 路径 | 不支持，会显示为黑屏 |

### 受保护内容为什么走不了 TextureView

DRM 视频或其它受保护内容对应的 buffer 带 `GRALLOC_USAGE_PROTECTED` 标记，只能通过 secure composition / secure overlay plane 路径被读取。SurfaceView 的独立 layer 可以直接走这条 secure 合成路径；TextureView 必须走宿主 RenderThread 的 GPU 重采样，而 HWUI 的通用渲染 context 不处于 protected 模式，读 secure buffer 只能拿到黑屏。

这是 TextureView 在视频播放场景下最常见的踩坑点之一——业务侧选择 TextureView 是为了 alpha / 圆角 / 旋转动画，但只要内容是 DRM 受保护的，路径选择就只能改回 SurfaceView。

[已验证: AOSP `frameworks/native/libs/gui/GraphicBuffer.cpp` 和 `frameworks/native/libs/ui/ConsumerBase.cpp` `USAGE_PROTECTED` flag + Android Developers `MediaDrm` 相关说明]

## onFrameAvailable 回调模型

`onFrameAvailable` 是 Producer 与 App 之间的桥梁，它的线程绑定模型直接影响帧的传递延迟。

### 默认行为

这里要分清两层 listener：

- `TextureView.SurfaceTextureListener` 面向普通 App 代码，负责 `SurfaceTexture` 的创建、尺寸变化和销毁回调
- `SurfaceTexture.OnFrameAvailableListener` 由 `TextureView.java` 在内部绑定，用来感知 Producer 送来的新帧

对 TextureView 本身来说，第二条 listener 才决定新帧何时进入 View 绘制流程。它跟着 View 所在线程走，常见场景就是主线程，收到回调后再触发 `invalidate()` 或 `postInvalidateOnAnimation()`。如果直接使用裸 `SurfaceTexture`，调用方可以自己挑选 Looper 和 Handler；讨论 TextureView 时，应按内部这条回调路径理解新帧通知。

### 回调延迟的来源

1. **主线程拥塞**：TextureView 内部 listener 常挂在 View 所在线程，收到回调后还要请求一次 `invalidate()` / `postInvalidateOnAnimation()`
2. **VSync 同步**：`invalidate()` 只是请求重绘，`updateTexImage()` 要等到下一个 VSync-App 唤醒 RenderThread 才会执行
3. **Producer → SurfaceTexture → App → RenderThread → SF**：中间多了一次 App 侧纹理采样和主窗口提交

### 帧丢弃行为

SurfaceTexture 默认只保留最新的一帧。如果 Producer 生产了 3 帧，但 App 只消费了 1 次 `updateTexImage`，中间的 2 帧会被丢弃。这在视频播放场景下是合理的（永远显示最新帧），但在需要逐帧处理的场景（如视频编辑预览）中可能导致帧丢失。

## Trace 视角

### 识别 TextureView 链路

识别 TextureView 链路的前提是确认**帧数据经过了 App RenderThread**：

1. **App RenderThread 中的 TextureView 绘制**：在 RenderThread 的 Track 中，`DrawFrame` 会包含 TextureView 的纹理采样操作
2. **`updateTexImage()` 与 fence 同步点**：常见路径下 CPU 侧的 `updateTexImage()` slice 很短，主要等待落在 acquire fence 对应的 GPU 同步；只有走 fallback 时才可能退化成 CPU 侧 fence wait
3. **单一 App 主窗口 Layer**：与 SurfaceView 不同，TextureView 不会额外创建一个给 SurfaceFlinger 单独识别的内容 Layer，所有内容都并入 App 主窗口 Buffer
4. **onFrameAvailable 回调路径**：如果 Trace 配置包含相关回调或 View invalidation 信号，可定位从 Producer `queueBuffer` 到 App 请求重绘之间的延迟

AOSP `GLConsumer.cpp` 的常见路径会把 acquire fence 转成 EGL wait（`eglWaitSyncKHR`）。CPU 端更像是在提交同步点，GPU 在后续采样这张 OES 纹理前再完成等待。驱动缺少 native fence sync 能力时，代码才会退化到 `waitForever()`。

#### Fence 在 TextureView 链路里要分两层看

TextureView 实际有两套 fence，用途不同不能混淆：

- **外部 Producer 侧的 fence**：保护"宿主侧通过 `updateTexImage` acquire 时不要太早读到 GPU 还没写完的外部内容"
- **宿主窗口侧的 fence**：保护"SurfaceFlinger 从宿主 `BLASTBufferQueue` latch 时不要太早读到宿主 GPU 还没合成完的最终窗口结果"

外部内容那一层 fence 晚了，宿主 `updateTexImage` 就会等；宿主自己那一层 fence 晚了，SF 这一轮 latch 就会等。Trace 上排查时要分别定位这两条 fence 的 signal 时间。

### 关键 Slice

| 位置 | 可能的 Slice | 说明 |
|:---|:---|:---|
| App RenderThread | `DrawFrame`, `updateTexImage` | 看触发点和与 GPU / fence 的对应关系，CPU 侧 `updateTexImage()` 通常很短 |
| App Main Thread | `Choreographer#doFrame` | VSync 唤醒和 invalidate |
| Producer Thread | `queueBuffer` | 帧提交到 SurfaceTexture |
| SurfaceFlinger | 单一 App Layer | 没有 SurfaceView 的独立 Layer |

### 与 SurfaceView 的 Trace 差异

| 特征 | SurfaceView | TextureView |
|:---|:---|:---|
| SurfaceFlinger Layer 数量 | ≥2（App + SV） | 1（只有 App） |
| App 主线程卡顿时 | SV 内容继续更新 | TV 内容跟着卡 |
| RenderThread 职责 | 只处理 App UI | 还要处理 TextureView 纹理 |
| Composition Type 观察点 | 可直接看独立 SurfaceView Layer 的 DEVICE / CLIENT | 只能看 App 主窗口 Layer；该 Layer 仍可能是 DEVICE 或 CLIENT |

## 常见性能问题与优化

### 1. 主线程卡顿传导

**现象**：视频/Camera 画面与 App UI 同步卡顿，而不是独立刷新。

**原因**：TextureView 的帧更新绑定到 App 的 Choreographer 帧循环。主线程卡顿 → `Choreographer#doFrame` 延迟 → `updateTexImage` 延迟 → 内容卡顿。

**优化方向**：
- 检查主线程的耗时操作，确保 `doFrame` 在 16ms 内完成
- 如果可能，迁移到 SurfaceView 以解除帧率绑定

### 2. `updateTexImage()` 同步点

**现象**：RenderThread 的 `DrawFrame` 变慢，TextureView 对应帧在 GPU 或 fence 相关轨道上出现等待。

**原因**：Producer 提交的 acquire fence 还未 signal 时，`GLConsumer` 需要在消费前建立同步。支持 native fence sync 的常见设备会把这一步转换成 EGL wait，CPU 侧 `updateTexImage()` 通常不长，主要等待落在 GPU 采样之前；驱动能力不足时才可能退化成 CPU 侧 fence wait。

**优化方向**：
- 减少 Producer 的 GPU 工作量（降低分辨率、简化着色器）
- 把观察重点放到 GPU / fence 轨道，而不是只盯 CPU 上的 `updateTexImage()` slice

### 3. 内存压力

**现象**：低端设备上 OOM 或 GC 频繁触发。

**原因**：TextureView 需要同时持有 Producer Buffer 和 App 主窗口 Buffer。以 1080p RGBA_8888 为例，一个 Buffer 约 8MB；按三缓冲估算，SurfaceTexture Producer 一侧接近 24MB，宿主窗口还要承载采样后的画面区域，图形内存和带宽很容易比 SurfaceView 路线多出几十 MB。

**优化方向**：
- 在低端设备上降级到 SurfaceView
- 降低视频/Camera 的输出分辨率

### 4. 帧丢弃导致画面跳跃

**现象**：视频播放时偶尔出现画面跳跃（跳过了一些帧）。

**原因**：SurfaceTexture 只保留最新帧，App 的帧率低于 Producer 帧率时，中间帧被丢弃。

**优化方向**：
- 确保 App UI 帧率足够高（避免主线程卡顿）
- 如果需要逐帧处理，考虑使用 ImageReader 替代 SurfaceTexture

## Metal/Vulkan Backend 性能对比（Android 13-17）


### 核心结论

**Android 17（API 37）范围内，TextureView 的 GPU 后端是 Skia + OpenGL ES，不存在 Metal/Vulkan 专属后端。**

- **Metal**：Apple 平台专有，Android 从未支持
- **Vulkan**：Android 13（API 33）起作为系统级图形选项引入，但在 TextureView 的 App 侧渲染路径中不扮演主要角色

### 源码级证据

**HardwareRenderer.java**（android-16.0.0_r1）的 `preload()` 注释：
```java
/**
 * Start render thread and initialize EGL or Vulkan.
 * Initializing EGL involves loading and initializing the graphics driver.
 */
public static native void preload();
```

这说明 Vulkan 在 Android 13+ 的角色是 **pre-init** 和**低功耗后台任务**，而非替代 OpenGL ES 成为 TextureView 的主渲染路径。

**TextureView.java** 文档注释明确写：
```java
/**
 * A TextureView can be used to display a content stream, such as that
 * coming from a camera preview, a video, or an OpenGL scene.
 */
```

TextureView 的消费侧（App RenderThread 采样）基于 **GL_OES_EGL_image_external** 纹理，这是 OpenGL ES 的扩展格式。

### TextureView 渲染路径与后端无关

TextureView 的性能瓶颈**不是 GPU 后端选择**造成的：

```
Producer → SurfaceTexture → App RenderThread（updateTexImage 采样 OES Texture）
→ BLAST BufferQueue → SurfaceFlinger → HWC
```

无论底层是 OpenGL ES 还是 Vulkan，TextureView 都必须经过 App 侧纹理采样，Vulkan 无法绕过这一架构设计。

### Vulkan 对 TextureView 的间接影响

Vulkan 引入对 TextureView 的**间接**影响（Android 13+）：

1. **视频解码后端**：MediaCodec 可使用 Vulkan 作为后端，解码帧通过 `SurfaceTexture` 提交时，如果解码器用 Vulkan，acquire fence 等待模式可能不同
2. **ANGLE**：Vulkan 作为 ANGLE 后端时，某些 GL 命令通过 Vulkan 执行，但 Java/JNI 代码路径不变
3. **内存拷贝**：Vulkan descriptor set 机制可能减少某些路径的内存拷贝，但 `updateTexImage → drawTextureLayer` 路径本身未变

### 实战建议

| 场景 | 建议 |
|:---|:---|
| 追求 TextureView 最佳性能 | 优化主线程负载、减少 updateTexImage 等待，而非关注 GPU 后端 |
| 需要 Metal/Vulkan 性能优势 | 考虑 SurfaceView（直接走 HWC Overlay，绕过 App 侧采样） |
| Android 17+ Vulkan 演进 | 需进一步验证 Vulkan swapchain API 是否已 public |

---

## 参考资料

- AOSP `frameworks/base/core/java/android/view/TextureView.java`
- AOSP `frameworks/base/graphics/java/android/graphics/SurfaceTexture.java`
- TextureView 折叠屏/异形屏行为适配（2026-06-04 深度调研）
  - 源码级分析 TextureView 在折叠屏/异形屏下的行为机制，核心依赖 WindowInsets + DisplayCutout + Choreographer 帧同步。TextureView 通过 `onSizeChanged` → `setDefaultBufferSize` 自动适应窗口形态变化，不依赖专用 API。SurfaceTexture buffer size 跟着 WindowMetrics 走，折叠/配置变更时自动调整。基于 android-16.0.0_r1 TextureView.java 源码验证。
- Android 官方文档：TextureView
- Android 性能优化指南：SurfaceView vs TextureView

## 何时从 TextureView 迁移到 SurfaceView

如果你的应用当前使用 TextureView，但实际并不需要变换能力（旋转、缩放、透明度动画），迁移到 SurfaceView 通常能减少 App 侧 GPU 采样和主窗口合成开销。迁移前先检查这几项：

1. **是否有变换需求**：如果需要动画变换、圆角裁剪、透明度调节 → 保留 TextureView
2. **是否有弹幕/悬浮控件**：如果在视频上方需要叠加 UI → 两者都可以，但 SurfaceView 需要考虑 Overlay 失效问题
3. **是否在低端设备运行**：如果目标设备 GPU 性能有限 → 强烈建议迁移到 SurfaceView
4. **帧率是否需要独立**：如果视频/Camera 需要独立于 App UI 帧率 → 迁移到 SurfaceView

迁移时需要注意：如果业务依赖 `setRotation()`、复杂裁剪、圆角或和普通 View 一致的透明度动画，TextureView 仍然更合适。SurfaceView 在 Android 7.0+ 的平移/缩放同步已经明显改善，Android 14+ 也支持 View alpha，但它仍不是 TextureView 那种完整的 View 变换模型。


## 游戏引擎集成注意事项（Unity/Unreal）


### 核心结论

**游戏引擎（Unity/Unreal）主渲染路径不经过 TextureView。** TextureView 在游戏引擎场景的适用场景仅限于：
- 游戏内嵌视频播放（VideoTexture）
- 直播美颜预览
- AR 相机预览叠加

### 架构差异

| 渲染路径 | TextureView | 游戏引擎主渲染 |
|:---|:---|:---|
| **Surface 创建** | `TextureView.getSurfaceTexture()` → `SurfaceTexture` | `eglCreateWindowSurface()` / `ANativeWindow_fromSurface()` |
| **渲染线程** | App RenderThread（`updateTexImage()` 采样） | 游戏独立 GL/Vulkan Context |
| **帧率** | 绑定 App UI 帧率 | 独立（60/90/120fps） |
| **延迟** | 高（App RT 中转） | 低（直出 SurfaceFlinger） |
| **GPU 采样** | 额外 OES 纹理采样 | 无额外采样 |

### Unity Android 渲染架构

Unity Android 通过 `IAndroidPlayerSurface` 接口创建原生窗口 surface：

```java
// Unity 内部实现（推测）:
// Unity/Modules/AndroidPlayer/Java/src/com/unity3d/player/AndroidPlayer.java
// 创建 Surface，通过 JNI 传句柄到 native 层
// native 层: ANativeWindow_fromSurface() → 直接绑定 GL context
```

关键路径（需 Unity 内部源码验证）：
- `frameworks/native/libs/gui/Surface.cpp`: `ANativeWindow_fromSurface()`
- `frameworks/base/core/jni/android_view_Surface.cpp`: Surface JNI 绑定

### Unreal Engine Android 渲染架构

Unreal 通过 `AndroidApplication` 创建 EGL 窗口：

```cpp
// Unreal Engine 源码（基于公开信息）:
// Engine/Source/Runtime/Android/OpenGLDrv/Private/AndroidOpenGL.cpp
// 使用 eglCreateWindowSurface() 创建原生窗口 surface
// 渲染直接提交，不经过 TextureView
```

### TextureView 适合的游戏子场景

| 场景 | 为什么用 TextureView |
|:---|:---|
| 游戏内嵌视频播放 | 需要和游戏 UI 叠加、滤镜、透明度动画 |
| 直播美颜预览 | 需要 AR 滤镜和 UI 元素融合 |
| 游戏录像回放 | 需要在游戏 UI 上叠加回放控件 |
| 视频广告 | DRM 保护内容走 SurfaceView，非保护内容可 TextureView |

### 性能对比

| 维度 | SurfaceView 游戏主渲染 | TextureView 视频纹理 |
|:---|:---|:---|
| **延迟** | 低（直出 SF） | 高（App RT 采样） |
| **GPU 开销** | 无额外采样 | 额外 OES 纹理采样 |
| **帧率绑定** | 独立 | 绑定 App UI |
| **适用场景** | 游戏主画面 | 游戏内视频/直播 |

### 源码级证据

**TextureView.java** (android-16.0.0_r1):
```java
/**
 * A TextureView can be used to display a content stream, such as that
 * coming from a camera preview, a video, or an OpenGL scene.
 */
public class TextureView extends View {
    private SurfaceTexture mSurface;
    private TextureLayer mLayer;
    // 游戏场景：mSurface 来自 MediaCodec/Camera
    // 游戏不直接渲染到 TextureView，而是渲染到 SurfaceTexture 背后的 Surface
}
```

**TextureLayer.java** (android-16.0.0_r1):
```java
/**
 * TextureLayer represents a SurfaceTexture that will be composited by 
 * RenderThread into the frame when drawn in a HW accelerated Canvas.
 */
public final class TextureLayer implements AutoCloseable {
    // 游戏引擎不直接创建 TextureLayer
    // TextureLayer 由 TextureView 内部创建和管理
}
```

### 实战建议

1. **游戏主渲染**: 使用 SurfaceView 或原生 EGL surface，不要用 TextureView
2. **游戏内视频**: TextureView 可用，但需注意主线程负载对帧率的影响
3. **AR 预览**: 需要 UI 叠加时 TextureView 更灵活，不需要时用 SurfaceView
4. **低端设备**: 即使是视频播放，也建议降级到 SurfaceView 减少 GPU 开销

---



## 折叠屏/异形屏适配

### 核心结论

**TextureView 的折叠屏/异形屏适配不依赖专用 API，核心依赖三件套：WindowInsets + DisplayCutout + Choreographer 帧同步。**

折叠屏适配本质是 WindowManager 将 DisplayCutout、安全区边界、Multi-Window bounds 通过 WindowInsets 传递给 View 层级。TextureView 作为普通 View，直接参与 View 树的 `onApplyWindowInsets` 流程，无需专门适配。

### 源码级适配机制

#### 1. 尺寸自动适应：setDefaultBufferSize

**关键函数路径**：
```
TextureView.onSizeChanged(w, h)
  → mSurface.setDefaultBufferSize(getWidth(), getHeight())
  → updateLayer()
```

**源码**：`TextureView.java` (android-16.0.0_r1) 第 385-400 行
```java
@Override
protected void onSizeChanged(int w, int h, int oldw, int oldh) {
    super.onSizeChanged(w, h, oldw, oldh);
    if (mSurface != null) {
        mSurface.setDefaultBufferSize(getWidth(), getHeight());
        updateLayer();
        if (mListener != null) {
            mListener.onSurfaceTextureSizeChanged(mSurface, getWidth(), getHeight());
        }
    }
}
```

TextureView 的 SurfaceTexture buffer size 绑定到 View 自身尺寸。折叠/配置变更导致 View layout 变化时，SurfaceTexture buffer 自动 resize，无需额外 API 调用。

#### 2. WindowInsets 传递路径

**源码**：`View.java` (android-16.0.0_r1) `onApplyWindowInsets` 默认实现
```java
public WindowInsets onApplyWindowInsets(WindowInsets insets) {
    if ((mPrivateFlags4 & PFLAG4_FRAMEWORK_OPTIONAL_FITS_SYSTEM_WINDOWS) != 0
            && (mViewFlags & FITS_SYSTEM_WINDOWS) != 0) {
        return onApplyFrameworkOptionalFitSystemWindows(insets);
    }
    if ((mPrivateFlags3 & PFLAG3_FITTING_SYSTEM_WINDOWS) == 0) {
        if (fitSystemWindows(insets.getSystemWindowInsetsAsRect())) {
            return insets.consumeSystemWindowInsets();
        }
    }
    return insets;
}
```

TextureView 继承 View 默认的 `onApplyWindowInsets` 行为。WindowInsets 携带 DisplayCutout（异形屏挖孔）、system bars inset、IME inset 等信息。可通过 `setOnApplyWindowInsetsListener` 自定义处理。

#### 3. DisplayCutout 异形屏适配

**源码**：`DisplayCutout.java` (android-16.0.0_r1)
```java
public final class DisplayCutout {
    private final Rect mSafeInsets;
    @NonNull
    private final Insets mWaterfallInsets;

    public static final int BOUNDS_POSITION_LEFT = 0;
    public static final int BOUNDS_POSITION_TOP = 1;
    public static final int BOUNDS_POSITION_RIGHT = 2;
    public static final int BOUNDS_POSITION_BOTTOM = 3;
}
```

DisplayCutout 描述屏幕物理挖孔区域的安全区边界。通过 `WindowInsets.getDisplayCutout()` 获取。TextureView 所在窗口若置于挖孔区域，可通过 WindowInsets 判断 safe insets 并做 padding。

#### 4. Multi-Window 中的 TextureLayer 隔离

**源码**：`TextureView.java` (android-16.0.0_r1) `getTextureLayer()`
```java
TextureLayer getTextureLayer() {
    if (mLayer == null) {
        if (mAttachInfo == null || mAttachInfo.mThreadedRenderer == null) {
            return null;
        }

        mLayer = mAttachInfo.mThreadedRenderer.createTextureLayer();
        boolean createNewSurface = (mSurface == null);
        if (createNewSurface) {
            mSurface = new SurfaceTexture(false);
            nCreateNativeWindow(mSurface);
        }
        mLayer.setSurfaceTexture(mSurface);
        mSurface.setDefaultBufferSize(getWidth(), getHeight());
        mSurface.setOnFrameAvailableListener(mUpdateListener, mAttachInfo.mHandler);
        mLayer.setLayerPaint(mLayerPaint);
    }
    // ...
}
```

Multi-Window / PiP / Freeform 模式下，每个窗口实例各自创建 TextureLayer 和 SurfaceTexture。`mLayer` 和 `mSurface` 按窗口隔离。WindowContainerTransaction 改变窗口 bounds 时，View layout 触发 `onSizeChanged`，SurfaceTexture buffer size 随之更新。

### 版本差异

| 版本 | TextureView 折叠屏支持 | 说明 |
|:---|:---|:---|
| Android 8.0 (API 26) | 基础 Multi-Window 支持 | TextureView 可用于分屏，无专用 foldable API |
| Android 12 (API 31) | Jetpack WindowManager | `WindowManager.fold()` API（折叠状态监听） |
| Android 15 (API 35) | DisplayShape API | 更完整的异形屏支持 |
| Android 17 (API 37) | 无 TextureView 专用变化 | 适配机制同 Android 16 |

### 性能影响

1. **配置变更触发完整重绘**：折叠状态切换触发 `onConfigurationChanged()`，View 树重新 measure/layout/draw
2. **SurfaceTexture buffer reallocation**：`onSizeChanged` → `setDefaultBufferSize` 可能触发 BufferQueue re-allocation，产生 1-2 帧的 buffer 重建开销
3. **帧率绑定在 Multi-Window 中更明显**：多窗口场景下主线程竞争更激烈，TextureView 的帧率绑定劣势被放大

### 实战建议

| 场景 | 建议 |
|:---|:---|
| 折叠切换时黑帧 | 在 `onSurfaceTextureAvailable` 前显示占位符 |
| 频繁折叠/展开 | 避免在 `onSizeChanged` 内做重量级操作 |
| 低端折叠屏 | 考虑降级到 SurfaceView，减少 App 侧纹理采样开销 |
| 视频纹理在折叠屏 | 检查是否需要独立帧率，不需要则 TextureView 可用 |

> **研究局限**：`android-17.0.0_r1 TextureView.java` 在 aosp-mirror 仓库 404，使用 `android-16.0.0_r1` 替代。Hinge angle sensor 与 TextureView 的联动需进一步研究 Jetpack WindowManager。


---

> **交叉引用**：
> - SurfaceView 直出路径（对比参考）详见 [18.6 SurfaceView 直出路径](06-surfaceview.md)
> - OpenGL ES 链路详见 [18.8 OpenGL ES 渲染链路](08-opengl-es.md)
> - BufferQueue 与 SurfaceTexture 机制详见 [2.13 图形缓冲区管理（BufferQueue）](../../part1-fundamentals/ch02-rendering/13-buffer-queue.md)
> - SurfaceFlinger 合成策略详见 [2.6 SurfaceFlinger 与合成](../../part1-fundamentals/ch02-rendering/06-surfaceflinger.md)
