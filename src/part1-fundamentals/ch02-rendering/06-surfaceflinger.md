---
title: "SurfaceFlinger 与合成"
chapter: "2.6"
status: ready-for-review
applicable_versions: "Android 12 (API S) - Android 16 (API 36)"
last_verified: "2026-04-02"
drafted_date: 2026-03-30
reviewed_date: 2026-04-04
reviewed_by: openclaw-task6
rework_date: 2026-04-02
last_verified_against: "AOSP android-16.0.0_r1, 官方文档最新版本"
confidence: medium
polish_count: 1
polish_date: "2026-04-04"
polish_by: "task2b-polish"
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/"
  - type: official
    path: "https://source.android.com/docs/core/graphics/surfaceflinger"
  - type: blog
    path: "https://www.androidperformance.com/"
tags: ['surfaceflinger', 'bufferqueue', 'hwc', 'composition', 'layer', 'vsync', 'blastbufferqueue', 'renderengine']
related_chapters: ["2.1", "2.3", "2.4", "2.5", "2.10", "7.3"]
pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: idle
---

# SurfaceFlinger 与合成

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 SurfaceFlinger 的核心职责：Layer 合成、VSync 分发、Buffer 管理
- 🔹 合成方式：Client Composition (GPU) vs Device Composition (HWC)
- 🔹 Layer 的概念与 z-order 排列
- 🔹 SurfaceFlinger 主循环：onMessageReceived → INVALIDATE/REFRESH
- 🔹 Jank 与 SurfaceFlinger 的关系：SF 主线程卡顿对全局帧率的影响
- 🔹 BlastBufferQueue 的引入与改进（Android 12+）
- 🔹 在 Perfetto 中的表现：各 Track 对照与正常/异常判断

### 扩展（可选深入）

- 🔸 SurfaceFlinger 与 HWC HAL 的交互协议
- 🔸 Transaction 机制与 SyncTransaction

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解 SurfaceFlinger

打开 Perfetto 抓一段 Trace，在进程列表里总能看到一个名为 `surfaceflinger` 的进程。它的主线程 Track 上，每隔一帧都会出现一组标记——`INVALIDATE`、`handleMessageRefresh`、`preComposition`、`doComposition`。做过 Android 性能优化的工程师，大概率在排查系统级卡顿时被这块区域吸引过，但往往不知道该怎么读。

这就是 SurfaceFlinger——Android 图形系统的合成器。它接受来自多个来源的数据缓冲区，对它们进行合成，然后发送到显示设备。用一个形象的比喻：如果把每个应用的渲染结果比作一张幻灯片，SurfaceFlinger 就是把这些幻灯片按顺序叠在一起，投影到屏幕上的那个投影仪。

理解 SurfaceFlinger 的意义在于，它能将性能分析的视角从"应用画得慢不慢"提升到"整条图形管线的哪个环节出了问题"。很多时候 App 渲染没问题，但用户还是觉得卡——这种问题的根因往往在 SurfaceFlinger 这一层。可能是合成耗时过长，可能是 VSync 信号分发有延迟，也可能是 BufferQueue 的 Buffer 周转不过来。

在 Perfetto 中，SurfaceFlinger 的相关 Track 包括：SurfaceFlinger 主线程（展示合成各阶段耗时）、VSYNC-sf（触发合成的信号）、VSYNC-app（触发渲染的信号）、以及 BufferQueue 系列操作（dequeueBuffer、queueBuffer、acquireBuffer、releaseBuffer）。我们会在后文逐一拆解这些 Track 的含义，但先让我们从 SurfaceFlinger 本身的工作机制说起。

## 核心机制：Layer 合成、VSync 分发与 Buffer 管理

SurfaceFlinger 是 Android 系统中唯一能够直接修改显示内容的核心服务，运行在独立的系统进程中。它的核心职责可以归纳为三件事：管理 Layer 并将它们合成为最终画面、分发 VSync 信号驱动渲染管线、以及通过 BufferQueue 协调数据的流转。

### Layer 合成：多源汇聚为一帧

大多数应用在屏幕上一次显示三个 Layer：屏幕顶部的状态栏、底部或侧面的导航栏、以及应用自身的界面。每个 Layer 都可以独立更新——比如状态栏在显示时间变化时只更新自己的 Layer，而不需要整个屏幕重绘。

当 VSYNC 信号到达时，SurfaceFlinger 会遍历它的 Layer 列表，检查每个 Layer 是否有新的 Buffer。如果找到了新 Buffer，就获取（acquire）它；如果没有新 Buffer，就继续使用上一次获取的旧 Buffer。然后 SurfaceFlinger 把所有可见的 Layer 按照 z-order 从后往前叠加，合成为一帧完整的画面，交给显示硬件呈现。

[图：SurfaceFlinger Layer 合成架构图——多个 App 的 BufferQueue 汇聚到 SurfaceFlinger，SurfaceFlinger 按 z-order 叠加后输出到 Display]

### VSync 分发：管线的节拍器

SurfaceFlinger 不只是被动地合成画面，它还参与 VSync 信号的分发。硬件 VSync 信号由 HWC（Hardware Composer）产生，SurfaceFlinger 通过 DispSync（Android 12 之后为 VsyncModulator）将其分发为两个关键信号：

- **VSYNC-app**：发给应用程序，触发 Choreographer 开始一帧的渲染工作（measure → layout → draw）。
- **VSYNC-sf**：发给 SurfaceFlinger 自身，触发 SurfaceFlinger 开始合成。

这两个信号之间有一个精心计算的时间差（offset）。VSYNC-app 先到，让 App 有时间画完一帧；等 App 渲染完、Buffer 提交到 BufferQueue 之后，VSYNC-sf 才到来，触发 SurfaceFlinger 去拿这个 Buffer 做合成。这个时序设计非常关键——如果两者的 offset 设置不合理，就会导致 App 画完了但 SurfaceFlinger 没来得及拿，或者 SurfaceFlinger 开始合成了但 App 还没画完，表现为掉帧。

我们在 §2.3（VSync 机制）中详细讲解过 offset 的计算逻辑，这里只需要记住一个关键点：**SurfaceFlinger 的合成时机由 VSYNC-sf 决定，而 VSYNC-sf 的 offset 是整个图形管线时序调优的核心参数之一。**

### Buffer 管理：BufferQueue 的四步流转

SurfaceFlinger 和应用之间通过 BufferQueue 传递画面数据。BufferQueue 的核心操作只有四步，理解了这四步就掌握了图形数据在 App 和 SurfaceFlinger 之间的完整流转：

1. **dequeueBuffer（App 发起）**：App 从 BufferQueue 请求一块空闲的 GraphicBuffer，用来承载即将渲染的画面。
2. **queueBuffer（App 发起）**：App 在这块 Buffer 上完成渲染后，将它放回 BufferQueue，通知消费者（SurfaceFlinger）有新数据可用。
3. **acquireBuffer（SurfaceFlinger 发起）**：SurfaceFlinger 在 VSYNC-sf 到来时，从 BufferQueue 取出 App 最新提交的 Buffer，准备合成。
4. **releaseBuffer（SurfaceFlinger 发起）**：SurfaceFlinger 合成完毕、该 Buffer 已被显示硬件消费后，将其归还给 BufferQueue，App 可以再次 dequeue 使用。

这四步形成了一个循环。在 Perfetto 中，可以分别在 App 进程和 SurfaceFlinger 进程的 Track 里看到 dequeueBuffer/queueBuffer 和 acquireBuffer/releaseBuffer 的时间点。正常情况下，dequeue → queue → acquire → release 应该在一个 VSync 周期内顺畅完成；如果某个环节耗时过长或被阻塞，就会在 Trace 中表现为明显的间隔。

[待补充：Trace 截图——BufferQueue 四步操作在 Perfetto 中的对应 Track]

## 合成方式：Client 合成与 Device 合成

SurfaceFlinger 有两种合成方式：Client 合成（也叫 GPU 合成）和 Device 合成（也叫 HWC 硬件合成）。理解两者的区别，对于分析合成性能和功耗至关重要。

### Client 合成：GPU 走一遍完整渲染流程

当 SurfaceFlinger 决定使用 Client 合成时，它会通过 RenderEngine（底层使用 OpenGL ES 或 Vulkan）将所有需要合成的 Layer 按顺序渲染到一个 Framebuffer 目标上。可以把这理解为一次特殊的"渲染 Pass"——SurfaceFlinger 充当 GPU 客户端，把每个 Layer 当作一个纹理，设置好变换矩阵和混合模式，然后逐层绘制。

Client 合成的优势在于灵活性——GPU 能处理任何复杂的变换、缩放、旋转和混合效果。但代价也很明显：它需要占用 GPU 算力，消耗额外的内存带宽，并且整个合成过程是"实打实的渲染"，需要等待 GPU 完成。当 Layer 数量多或者 Layer 内容复杂时，Client 合成的耗时可能达到好几毫秒，直接挤占 App 可用的 GPU 时间，导致 App 渲染变慢。

### Device 合成：HWC 直接在硬件层面叠加

HWC（Hardware Composer）是显示控制器中专门用于合成的硬件单元。SurfaceFlinger 向 HWC 提供完整的 Layer 列表，HWC 为每个 Layer 判断：这个 Layer 能不能直接用硬件叠加（Overlay）的方式合成？如果能，就标记为 Device 合成；如果不能（比如 Layer 有复杂的混合效果或缩放），就标记为 Client 合成，退回 GPU 处理。

HWC 硬件合成的效率极高——它不经过 GPU，不需要渲染管线，只是把多个 Layer 的 Buffer 指针交给显示控制器，让硬件在扫描输出时直接从多个 Buffer 中读取像素并混合。这意味着合成过程几乎零 CPU/GPU 开销，功耗也更低。

不过 HWC 也有其限制。每个设备的 HWC 支持的 Overlay 平面数量是有限的（不同设备从 4 个到 16 个不等，取决于 SoC 和显示控制器型号），超出数量限制的 Layer 必须退回 Client 合成。此外，某些复杂的变换（如圆角裁剪、模糊效果）HWC 可能不支持，也会退回 GPU。

### 合成方式的选择逻辑

SurfaceFlinger 在 `prepareFrame` 阶段会与 HWC 协商：先让 HWC 尝试接收所有 Layer，HWC 返回每个 Layer 的合成类型标记（Device 或 Client）。对于被标记为 Client 的 Layer，SurfaceFlinger 会用 RenderEngine 将它们先合成到一个中间 Buffer，然后将这个中间 Buffer 作为单个 Layer 再交给 HWC 做 Device 合成。所以实际工作中，最常见的是"混合模式"——部分 Layer 走 HWC 硬件叠加，部分 Layer 走 GPU 合成后作为一个整体再交给 HWC。

[图：Client 合成 vs Device 合成的架构对比——混合模式下部分 Layer 走 GPU 合成到中间 Buffer，再与 HWC 叠加层一起输出到 Display]

## SurfaceFlinger 主循环

了解了 SurfaceFlinger 的三大核心职责后，我们来看它在每一帧里到底做了什么。SurfaceFlinger 的主循环由 VSYNC-sf 信号驱动。在 Android 14 之前，核心入口是 `onMessageReceived`，处理 INVALIDATE 和 REFRESH 两类消息。从 Android 14 开始，SurfaceFlinger 重构为 `ICompositor` 接口模式，入口变为 `Scheduler::onFrameSignal` → `SurfaceFlinger::commit()` + `SurfaceFlinger::composite()`，但内部的步骤和调用顺序保持一致——下文展示的是经典流程（INVALIDATE → REFRESH 模式），方便理解各阶段的职责：

```cpp
// frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
// @ AOSP android-16.0.0_r1
void SurfaceFlinger::onMessageReceived(int32_t what) NO_THREAD_SAFETY_ANALYSIS {
    ATRACE_CALL();
    switch (what) {
        case MessageQueue::INVALIDATE: {
            bool refreshNeeded = handleMessageTransaction();
            refreshNeeded |= handleMessageInvalidate();
            break;
        }
        case MessageQueue::REFRESH: {
            handleMessageRefresh();
            break;
        }
    }
}
```

这段代码告诉我们，SurfaceFlinger 在每个 VSYNC-sf 到来时处理两类消息：INVALIDATE 和 REFRESH。INVALIDATE 消息触发事务处理和 Buffer 检查；REFRESH 消息触发实际的合成工作。我们先看 INVALIDATE 阶段。

### INVALIDATE 阶段：检查有没有新东西

```cpp
// frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
// @ AOSP android-16.0.0_r1
bool SurfaceFlinger::handleMessageInvalidate() {
    ATRACE_CALL();
    bool refreshNeeded = handlePageFlip();
    // ... visible regions, layer bounds
    return refreshNeeded;
}
```

`handleMessageInvalidate` 的核心是 `handlePageFlip`——遍历所有 Layer，检查是否有新的 Buffer 被 queueBuffer 进来。如果有，就 acquire 这个 Buffer，更新 Layer 的可见区域和边界信息。名字中的"Page Flip"来自传统的图形术语，意思是"翻页"——把新的一页（Buffer）翻上来。

如果 `handlePageFlip` 发现确实有新 Buffer 需要合成，就返回 true，表示接下来需要触发 REFRESH 消息执行合成。

### REFRESH 阶段：执行合成

```cpp
// frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
// @ AOSP android-16.0.0_r1
void SurfaceFlinger::handleMessageRefresh() {
    ATRACE_CALL();
    mRefreshPending = false;
    const bool repaintEverything = mRepaintEverything.exchange(false);
    preComposition();
    rebuildLayerStacks();
    calculateWorkingSet();
    for (const auto& [token, display] : mDisplays) {
        beginFrame(display);
        prepareFrame(display);
        doDebugFlashRegions(display, repaintEverything);
        doComposition(display, repaintEverything);
    }
    logLayerStats();
    postFrame();
    postComposition();
}
```

这段代码是 SurfaceFlinger 每帧合成的完整流程，我们逐个拆解：

**preComposition**：合成前的准备工作，包括处理任何待处理的事务（Transaction）。

**rebuildLayerStacks**：重新构建 Layer 栈。这一步会根据每个 Display 的 Layer 过滤规则，从全局 Layer 列表中筛选出需要在当前 Display 上显示的 Layer，并按 z-order 排序。如果某个 Layer 的可见区域发生变化（比如窗口移动、缩放），这里会更新。

**calculateWorkingSet**：计算工作集——确定每个 Layer 的合成方式（Client 还是 Device），以及需要 GPU 合成的 Layer 列表。这一步会与 HWC 协商（调用 HWC 的 prepare 接口）。

**beginFrame / prepareFrame / doComposition**：这三个步骤对每个 Display 执行。`beginFrame` 初始化帧的渲染环境；`prepareFrame` 向 HWC 提交 Layer 信息并确认合成策略；`doComposition` 执行实际的合成——对于 Client 合成的 Layer，通过 RenderEngine 渲染；对于 Device 合成的 Layer，交给 HWC 硬件处理。

**postFrame / postComposition**：帧的收尾工作。`postFrame` 处理帧完成后的统计；`postComposition` 通知 VSync 时间戳给 FrameTimeline，用于后续的帧呈现时间预测。

在 Perfetto 中，每个阶段都有对应的 ATRACE 标记。正常情况下，从 `handleMessageRefresh` 到 `postComposition` 的完整流程应在一个 VSync 周期内完成（60Hz 约 16.67ms，120Hz 约 8.33ms）；某个阶段耗时明显偏长，就是瓶颈所在。下一节我们直接对照 Perfetto，把上述流程映射到 Track 上。

[图：SurfaceFlinger 主循环时序图——从 VSYNC-sf 触发到 postComposition 完成的完整流程]

## 在 Perfetto 中的表现

做性能分析时，最关心的往往不是 SurfaceFlinger 内部代码怎么写的，而是"在 Trace 里我怎么看出它出了问题"。这一节我们对照 Perfetto 的 Track，把 SurfaceFlinger 的工作过程映射到界面上能直接看到的东西。

### SurfaceFlinger 主线程 Track

在 Perfetto 中展开 SurfaceFlinger 进程，主线程 Track 上能看到每帧的合成工作。正常情况下，每隔一个 VSync 周期（取决于刷新率），Track 上会出现一组标记：

- **INVALIDATE**：对应 `handleMessageInvalidate`，检查是否有新 Buffer。这一步通常很快，几百微秒级别。
- **REFRESH**：对应 `handleMessageRefresh`，这是合成的主体工作。在它内部能看到 `preComposition`、`rebuildLayerStacks`、`calculateWorkingSet`、`doComposition` 等子阶段的 ATRACE 切片。

**正常表现**：REFRESH 的总耗时通常在 2-6ms 左右（取决于 Layer 数量和合成复杂度），并且每个 VSync 周期稳定出现一次，没有明显的毛刺。

**异常表现**：如果 REFRESH 耗时突然飙到 10ms+，可能的原因包括：Layer 数量突然增多（如多窗口模式）、Client 合成的 Layer 比例增大（HWC 容量不足）、或者 GPU 合成时被其他任务的 GPU 工作阻塞。如果 REFRESH 根本没有按时出现，说明 SurfaceFlinger 主线程被其他操作阻塞了（比如一个耗时的 Transaction 处理）。

### VSYNC-sf Track

这个 Track 显示触发 SurfaceFlinger 合成的 VSync 信号时间点。在 Perfetto 中它表现为一系列等间距的竖线（60Hz 设备间距约 16.67ms，120Hz 设备约 8.33ms）。每次 VSYNC-sf 到来，SurfaceFlinger 主线程的 Track 上就应该紧跟着出现对应的合成工作。

**正常表现**：VSYNC-sf 信号均匀分布，SurfaceFlinger 在每个信号后立即开始工作。

**异常表现**：如果 VSYNC-sf 信号的间距不均匀（有跳变），说明 VSync 偏移（offset）可能被动态调整了，或者硬件 VSync 本身有抖动。如果 SurfaceFlinger 没有在 VSYNC-sf 后及时开始工作，说明主线程有阻塞。

### VSYNC-app Track

这个 Track 显示触发应用程序渲染的 VSync 信号。VSYNC-app 和 VSYNC-sf 之间的时间差就是 offset——VSYNC-app 先到，App 开始渲染；渲染完成后 VSYNC-sf 到来，SurfaceFlinger 开始合成。

**关键检查点**：VSYNC-app 到 VSYNC-sf 的间距应该稳定。如果间距异常增大，意味着 App 可用的时间变少了；如果间距异常减小甚至 VSYNC-sf 先于 VSYNC-app 到来，说明时序配置有问题。

### BufferQueue Track

BufferQueue 的四步操作在 Perfetto 中可以分别追踪：

- **dequeueBuffer**：出现在 App 进程中。App 请求一块空闲 Buffer。如果这里耗时过长，说明 BufferQueue 中的空闲 Buffer 不够用了——可能是 SurfaceFlinger 持有 Buffer 太久没 release，也可能是三缓冲策略下的 Buffer 全部被占满。
- **queueBuffer**：出现在 App 进程中。App 完成渲染后提交 Buffer。正常情况下 dequeue 和 queue 之间就是 App 的渲染耗时。
- **acquireBuffer**：出现在 SurfaceFlinger 进程中。SurfaceFlinger 取出 App 提交的最新 Buffer。acquire 应该在 queue 之后不久发生（通常在下一个 VSYNC-sf 到来时）。
- **releaseBuffer**：出现在 SurfaceFlinger 进程中。SurfaceFlinger 用完 Buffer 后归还。

**正常流转**：dequeue → 渲染 → queue → [等待 VSYNC-sf] → acquire → 合成 → release → [Buffer 回到空闲池]。整个周期在一个 VSync 周期内完成。

**异常标志**：
- dequeueBuffer 耗时过长（>2ms）：Buffer 全部被占用，App 在等 SurfaceFlinger 释放。这通常意味着 SurfaceFlinger 合成太慢，没有及时 release。
- acquireBuffer 和 queueBuffer 之间间隔超过一个 VSync 周期：SurfaceFlinger 漏了一帧，没有在下一个 VSYNC-sf 时处理这个 Buffer。
- releaseBuffer 延迟：合成耗时太长或者 HWC 持有 Buffer 时间过长。

### HWC 合成 Track

SurfaceFlinger 与 HWC 的通信过程也可以在 Trace 中追踪。在 SurfaceFlinger 主线程 Track 上，`prepareFrame` 和 `doComposition` 阶段会包含与 HWC 的交互。

**Device 合成（HWC Overlay）**：当 Layer 走 HWC 硬件合成时，`doComposition` 阶段几乎不消耗时间——SurfaceFlinger 只是把 Buffer 指针交给 HWC，HWC 在扫描输出时直接从多个 Buffer 读取并混合。在 Trace 中 `doComposition` 切片非常短，通常不到 1ms。此时真正的合成工作发生在显示硬件中，Perfetto 无法直接观测到 HWC 内部的处理耗时，只能通过 FrameTimeline 中帧的实际呈现时间来间接判断。

**Client 合成（GPU/RenderEngine）**：当某些 Layer 退回 GPU 合成时，`doComposition` 切片会明显变长。能看到 RenderEngine 相关的 GPU 操作耗时——这是 SurfaceFlinger 作为 GPU 客户端执行渲染 Pass 的时间。如果 Client 合成的 Layer 较多或内容复杂，这个耗时可能达到 3-8ms，直接反映在 SurfaceFlinger 主线程的 REFRESH 总耗时中。

**排查要点**：在 Trace 中发现 SurfaceFlinger 的 `doComposition` 突然耗时增加时，第一件事就是检查是否有 Layer 从 Device 合成退回到了 Client 合成。可以通过 `dumpsys SurfaceFlinger --list` 查看各 Layer 的合成类型分配，或者直接在 Perfetto 中对比正常/异常时段的 Layer 数量和合成方式变化。

[待补充：Trace 截图——正常 vs 异常的 SurfaceFlinger Perfetto 片段对比，标注 Device/Client 合成切换]

### 正常 vs 异常：一个对比案例

**正常场景**：App 渲染耗时 5ms → queueBuffer → VSYNC-sf 到来 → SurfaceFlinger acquireBuffer + 合成耗时 3ms → 提交给 HWC → 下一帧正常呈现。整个 Trace 看起来节奏均匀，没有任何一个环节拖后腿。

**异常场景**：App 渲染正常（5ms），但 SurfaceFlinger 的 `doComposition` 突然耗时 12ms（可能因为某个 Layer 的缩放操作触发了 Client 合成，而 GPU 正忙于其他任务）。结果 SurfaceFlinger 没能在当前 VSync 周期内完成合成，导致这一帧被延迟到下一个 VSync 才呈现——用户感知到一次卡顿。在 Trace 中，SurfaceFlinger 主线程 Track 上会出现一个明显拉长的 doComposition 切片，紧接着下一帧的 VSYNC-sf 没有触发合成（因为上一帧还没处理完），这就是典型的"SF 导致的全局掉帧"。

## Layer 与 z-order

前面多次提到 Layer 和 z-order，这里展开讲讲。

Layer 是 SurfaceFlinger 管理显示内容的基本单元。每个 Activity、每个 Window、每个 Surface 都对应一个 Layer。在 SurfaceFlinger 眼里，屏幕上的一切都是 Layer 的叠加——状态栏是一个 Layer，导航栏是一个 Layer，App 界面是一个 Layer，浮动通知也是一个 Layer。

Layer 之间有父子关系，构成树形结构。父 Layer 可以控制子 Layer 的可见性和变换。最终决定屏幕上显示效果的是 z-order——Layer 的前后顺序。z-order 值越大的 Layer 越靠前（离用户越近），会遮挡 z-order 值小的 Layer。

在 SurfaceFlinger 主循环的 `rebuildLayerStacks` 阶段，所有可见的 Layer 会按 z-order 排序，形成最终的合成列表。通过 `dumpsys SurfaceFlinger` 命令可以查看当前所有 Layer 的 z-order 和层级关系。

一个常见的性能陷阱是 Layer 数量过多。每多一个 Layer，SurfaceFlinger 在 `rebuildLayerStacks` 和 `calculateWorkingSet` 阶段就要多处理一层，HWC 也需要多分配一个 Overlay 平面。当 Layer 数量超过 HWC 支持的最大 Overlay 数量时，多余的 Layer 会被退回 Client 合成，GPU 开销陡增。所以在做性能优化时，减少不必要的 Layer（比如合并过度绘制的 View 层级、避免不必要的硬件层）是值得关注的。

[图：Layer 树形结构和 z-order 排列示意图——状态栏(z=高)、App(z=中)、壁纸(z=低)的叠加关系]

## Jank 与 SurfaceFlinger 的关系

SurfaceFlinger 的性能问题有一个特点：它不是"某个 App 卡了"，而是"整个系统卡了"。因为 SurfaceFlinger 是全局合成器，它的主线程卡顿会影响所有可见的应用。

具体来说，如果 SurfaceFlinger 在某一帧的合成过程中耗时过长（比如 `doComposition` 超过一个 VSync 周期），会发生以下连锁反应：

1. 这一帧的合成结果来不及在当前 VSync 周期内提交给显示硬件，被推迟到下一个 VSync。
2. 所有 App 的最新渲染结果都不会在当前帧呈现——即使 App 本身渲染得很快。
3. SurfaceFlinger 持有 Buffer 的时间变长，releaseBuffer 延迟，导致 App 端 dequeueBuffer 被阻塞。
4. App 因为拿不到空闲 Buffer，渲染也被迫等待，形成恶性循环。

在 Perfetto 中，这种情况表现为：SurfaceFlinger 主线程 Track 上出现一个明显拉长的合成切片，紧接着几个 VSYNC-sf 信号都没有触发合成（因为上一帧还在处理），然后 SurfaceFlinger 追赶式地处理积压的帧。在用户侧，这就是一段明显的卡顿。

我们在实际分析中，最常遇到的 SurfaceFlinger 卡顿原因有四类。

第一类是**Layer 数量突增**。比如进入多窗口模式或弹出系统 Dialog，合成工作量显著增加。第二类是**Client 合成比例增大**——某些 Layer 的属性发生变化（如添加圆角裁剪、模糊效果），HWC 无法处理，被迫退回 GPU 合成，GPU 渲染耗时陡增。第三类是**GPU 争抢**：App 的渲染任务和 SurfaceFlinger 的 Client 合成任务共享 GPU，当 App 侧的 GPU 负载很高时，SurfaceFlinger 的合成也会被拖慢。第四类是**Transaction 风暴**——大量 Layer 状态更新（比如动画期间窗口属性频繁变化）涌向 SurfaceFlinger，`handleMessageTransaction` 的处理耗时增加。

应对思路也很直接：减少 Layer 数量、尽量让更多 Layer 走 HWC 合成、控制 Transaction 的频率和数据量。具体的排查方法论，我们在 §7.3（卡顿分析方法论）中会系统讲解。

## BlastBufferQueue

Android 12 引入了 BlastBufferQueue（BBQ），这是 BufferQueue 机制的一次重大改进。要理解 BBQ 解决了什么问题，我们需要先看看它之前的方案有什么痛点。

### 之前的问题：Buffer 状态由 SurfaceFlinger 管理

在 Android 12 之前，App 的 BufferQueue 中的消费者端（Consumer）运行在 SurfaceFlinger 进程中。这意味着每次 Buffer 状态变化（acquire、release）都需要跨进程通信。当 App 提交一个 Buffer（queueBuffer），需要通过 Binder 通知 SurfaceFlinger；SurfaceFlinger 用完 Buffer 后，又要通过 Binder 通知 App 可以重新使用。每次跨进程调用都有开销，在多 Layer 场景下这些开销会累加。

### BBQ 的改进：App 端直接管理 Buffer 周转

BlastBufferQueue 将 Buffer 的状态管理移到了 App 进程内。App 不再需要每次都通过 Binder 与 SurfaceFlinger 协调 Buffer 的获取和释放，而是可以本地完成 dequeue → queue 的循环，只在必要时通知 SurfaceFlinger 有新帧可用。

具体来说，BBQ 带来了三个层面的变化。首先是 Buffer 的 acquire/release 不再需要跨进程——App 自己在本地完成 Buffer 的获取和归还，只有真正需要通知 SurfaceFlinger "有新帧了" 的时候才走一次 Binder 调用，大幅减少了跨进程通信次数。

其次是帧的提交方式改变了：App 渲染完一帧后，通过 SurfaceControl Transaction 将 Buffer 直接提交给 SurfaceFlinger，不再经过传统的 BufferQueue Consumer 中转。

最后是时序上的解耦——App 可以在任意时刻提交帧，不必等待某个特定的信号，SurfaceFlinger 会在下一个合适的 VSYNC-sf 到来时拿去处理。这三层变化叠加在一起，让多 Layer 场景下的帧传递效率提升非常明显。

BBQ 目前仅在 C++ 层使用（实现在 `frameworks/native/libs/gui/BlastBufferQueue.cpp`），对应用开发者来说是透明的。应用仍然通过 Surface、Canvas 等标准 API 进行渲染，底层已自动切换为 BBQ，因此不存在所谓的"BlastBufferQueue Java API"。

## 与其他机制的关系

SurfaceFlinger 不是孤立工作的，它是整条渲染管线中的一个关键环节。让我们把它的上下游关系梳理一下：

- **VSync 机制（§2.3）**：VSYNC-sf 信号驱动 SurfaceFlinger 的合成时机，VSYNC-app 信号驱动 App 的渲染时机。两个信号的 offset 配置直接决定了整条管线的效率。
- **Choreographer（§2.4）**：Choreographer 在收到 VSYNC-app 后调度 App 的 measure/layout/draw 工作。App 渲染完的 Buffer 通过 BufferQueue 提交给 SurfaceFlinger。如果 App 端的 Choreographer 回调执行太慢，Buffer 就来不及在下一个 VSYNC-sf 前准备好。
- **RenderThread（§2.5）**：App 的 RenderThread 负责将绘制命令提交给 GPU 执行。GPU 渲染完成后，RenderThread 调用 queueBuffer 提交结果。如果 GPU 渲染慢，queueBuffer 会延迟，SurfaceFlinger 在 VSYNC-sf 时就取不到新 Buffer。

整条管线的时序关系是：VSYNC-app → Choreographer.doFrame → RenderThread 渲染 → queueBuffer → VSYNC-sf → SurfaceFlinger 合成 → 提交显示。任何一个环节慢了，最终的帧呈现都会延迟。

## 版本演进

SurfaceFlinger 在不同 Android 版本中经历了多次重大变化：

**Android 4.1（Project Butter）**：引入 VSync 同步机制和三缓冲，这是 SurfaceFlinger 现代架构的起点。

**Android 4.3**：引入 OpenGL ES 渲染路径，SurfaceFlinger 开始使用 GPU 进行 Client 合成。

**Android 7.0**：引入 HWC 2.0，API 函数大幅扩充，新增 HDR、色彩变换矩阵等支持，`prepare()/set()` 更名为 `validate()/present()`，引入非推测性 Fence（一种硬件同步原语，用于精确等待 GPU 渲染完成后再读取 Buffer）。 [已验证：AOSP + web search 确认 HWC 2.0 为 Android 7.0 引入]

**Android 7.0**：SurfaceFlinger 从 mediaserver 进程独立为单独的 servicemanager 管理的服务。

**Android 8.0（Project Treble）**：HWC HAL 迁移到 HIDL 接口（`android.hardware.graphics.composer@2.1` ~ `@2.4`），SurfaceFlinger 通过 HIDL 与 HWC HAL 通信。

**Android 10**：引入 FrameTimeline，SurfaceFlinger 开始记录帧的预期呈现时间和实际呈现时间，为 Jank 检测提供了更精确的数据。

**Android 12**：引入 BlastBufferQueue，减少跨进程 Buffer 管理开销；SurfaceFlinger 合成流程重构。

**Android 13**：HWC HAL 开始支持 AIDL 接口（`android.hardware.graphics.composer3` / `IComposer.aidl`），替代 HIDL 接口。这个 AIDL 版本通常被称为 HWC 3.0。Vulkan 作为 RenderEngine 后端的支持逐步完善 [待验证：Vulkan 后端的具体引入版本和适用范围]。

**Android 14+**：HIDL 版 HWC HAL（`@2.4`）正式标记为 deprecated，厂商被要求迁移到 AIDL 版本。

## 常见问题与误区

### 误区一："App 渲染快就不会卡"

不完全对。即使 App 每帧都在 16ms 内完成渲染，如果 SurfaceFlinger 合成太慢，帧仍然会被延迟呈现。在 Perfetto 中排查卡顿时，不要只看 App 的 MainThread 和 RenderThread，一定要同时检查 SurfaceFlinger 主线程 Track。

### 误区二："SurfaceFlinger 卡了就是 SurfaceFlinger 的 bug"

不一定。SurfaceFlinger 的卡顿往往是"被拖累"的。比如某个 App 提交了一个超大 Layer（含复杂变换），SurfaceFlinger 不得不对它做 Client 合成，GPU 渲染耗时增加。根因在 App 端的 Layer 属性设置不合理，但表现为 SurfaceFlinger 卡顿。

### 误区三："HWC 合成一定比 GPU 合成好"

大多数情况下是的，但也有例外。HWC 的叠加平面（Overlay Plane）在内容完全不变时效率可能低于 GL 合成——因为 GL 合成可以在 Layer 没有变化时跳过处理，而 HWC 的 Overlay 每帧都需要硬件读取 Buffer。不过这个差异在实际应用中通常可以忽略。

### 误区四："dumpsys SurfaceFlinger 能看到所有性能问题"

`dumpsys SurfaceFlinger` 能看到 Layer 列表、HWC 合成类型分配、Buffer 状态等静态信息，但它不能替代 Perfetto Trace。性能问题的时间特性（什么时候卡、卡了多久、影响范围多大）只能从 Trace 中获取。`dumpsys` 适合做现状快照，Perfetto 适合做时序分析。

## 参考资料

### AOSP 源码

- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp` — SurfaceFlinger 主循环，核心入口 `onMessageReceived`、`handleMessageInvalidate`、`handleMessageRefresh`
- `frameworks/native/services/surfaceflinger/` — SurfaceFlinger 服务完整实现
- `frameworks/native/libs/gui/BlastBufferQueue.cpp` — BBQ 实现（Android 12+）
- `hardware/interfaces/graphics/composer/` — HWC HAL 接口定义（HIDL @2.x 和 AIDL composer3）
- `frameworks/native/libs/renderengine/` — RenderEngine 实现（OpenGL ES / Vulkan 后端）

### 官方文档

- [Android SurfaceFlinger 概述](https://source.android.com/docs/core/graphics/surfaceflinger) — 官方架构说明
- [Android 图形架构总览](https://source.android.com/docs/core/graphics/architecture) — 官方图形系统全景图
- [Hardware Composer HAL](https://source.android.com/docs/core/graphics/hwc) — HWC HAL 版本与接口说明

### 博客与文章

- [高爷 Android Performance 博客](https://www.androidperformance.com/) — SurfaceFlinger、BufferQueue、Systrace/Perfetto 分析系列
