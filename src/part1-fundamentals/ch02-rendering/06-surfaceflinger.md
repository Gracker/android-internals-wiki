---
title: "SurfaceFlinger 与合成"
chapter: "2.6"
section: "2.6"
status: finalized
pipeline_stage: ready-to-publish
applicable_versions: "Android 12 (API S) - Android 17 (API 37)"
last_verified: "2026-05-10"
drafted_date: 2026-03-30
reviewed_date: "2026-05-18"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
rework_date: 2026-04-02
last_verified_against: "AOSP android-12.0.0_r1, android-13.0.0_r1, android-14.0.0_r1, android-16.0.0_r1 (SurfaceFlinger / BLAST BufferQueue / HWC 2-HWC 3) + source.android.com HWC docs"
confidence: high
polish_count: 1
polish_date: "2026-04-04"
polish_by: "task2b-polish"
task9_reviewed_date: "2026-05-19"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-12T03:20:00+08:00"
last_task9_audit: "2026-06-12"
last_task9_autofix_at: "2026-06-12"
sources:
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/CompositionEngine/"
  - type: official
    path: "https://source.android.com/docs/core/graphics/surfaceflinger"
  - type: blog
    path: "https://www.androidperformance.com/"
tags: ['surfaceflinger', 'bufferqueue', 'hwc', 'composition', 'layer', 'vsync', 'blastbufferqueue', 'renderengine']
related_chapters: ["2.1", "2.3", "2.4", "2.5", "2.10", "2.13", "2.16", "7.3"]
task6_state: reviewed
task9_state: "reviewed"
task9_result: "auto-fixed"
task2b_state: "fixed"
task2b_result: "fixed"
last_task2b_at: "2026-06-05T04:53:38+08:00"
review_notes: "2026-04-26 task9 deep-review: needs-rework。P0 1，P1 2，P2 2。2026-04-27 task6 re-review (revisiting): pass-light-edit。比喻降格1处已修复。无B类大问题。；2026-04-27 task9 deep-review: needs-rework。P0 1，P1 2，P2 0。2026-04-27 task2b: fixed BufferQueue release wording, VSYNC-app/SF offset direction, and Layer/CompositionEngine stage anchors。；2026-04-28 task9 deep-review: pass-tech-review。P0 0，P1 0，P2 2。自动晋升 finalized。；2026-05-31 task6 revisiting review: pass-light-edit，L1/L2 问题修复完成，L3/L4 标注等待 Task2B。"
task6_reviewed_date: "2026-06-12"
last_task6_at: "2026-06-12T08:10:00+08:00"
last_task6_audit: "2026-07-03"
last_task6_review_log: "logs/review/2026-05-31-15-review.md"
task6_review_notes: "2026-05-18 Task6：L1 高频词「真正」压降至 2 次，修正结构性过渡语并清理重复 frontmatter；保留 Task9 已登记 Android 13 主循环版本边界回炉项，等待 Task2B。"
task9_review_notes: "2026-05-13 task9 deep-review: needs-rework。P0 3 / P1 1 / P2 0；HWC Android 16 DisplayLuts/CLIENT_BYPASS、Android 12 onMessageReceived 签名、Pacesetter/FrameTargeter 版本线需回炉。；2026-05-15 task2b: fixed DisplayLuts 降级为待验证, CLIENT_BYPASS 修正为 vendor-specific, onMessageReceived 签名修正, Pacesetter 版本线修正为 Android 14+。；2026-05-15 task9 deep-review: needs-rework。P0 2 / P1 0 / P2 0；新增问题已写入 queue，等待 Task2B 回炉。；2026-05-18 task9 deep-review: P0 1 / P1 0 / P2 1；Android 13 SurfaceFlinger 主循环误归入 INVALIDATE/REFRESH 旧模型，需 Task2B 修正；多显示 composite 并行/Perfetto 分组说法降级为建议。；2026-05-19 task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 0；Android 13+ commit/composite、Android 15+ FrameTargeter 与 HWC 待验证项复核通过；自动晋升 finalized。；2026-06-12 task9 idle audit: auto-fixed HWC2 getRequests 示例、composer Composition HIDL/AIDL 路径与枚举边界、Android 17 未公开 tag 引用边界。"
last_task9_review_log: "logs/deep-review/2026-06-12-03-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-12
---

# SurfaceFlinger 与合成

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 SurfaceFlinger 的核心职责：Layer 合成、VSync 分发、Buffer 管理
- 🔹 合成方式：Client Composition (GPU) vs Device Composition (HWC)
- 🔹 Layer 的概念与 z-order 排列
- 🔹 SurfaceFlinger 主循环：Android 12 为 onMessageReceived → INVALIDATE/REFRESH，Android 13+ 为 commit/composite
- 🔹 Jank 与 SurfaceFlinger 的关系：SF 主线程卡顿对全局帧率的影响
- 🔹 BLAST BufferQueue 的版本边界（Android 11 进入主线，Android 12+ 观察口径继续完善）
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

打开 Perfetto 抓一段 Trace，在进程列表里总能看到一个名为 `surfaceflinger` 的进程。它的主线程 Track 上，每隔一帧都会出现一组 slice，具体名称因 Android 版本而异：Android 12 常见 `INVALIDATE`、`REFRESH`，Android 13+ 更常见 `commit`、`composite`、`present`。做过 Android 性能优化的工程师，大概率在排查系统级卡顿时留意过这块区域，但往往不知道该怎么读。

这就是 SurfaceFlinger——Android 图形系统的合成器。它接收各应用提交的图形缓冲区，按 z-order 叠加后输出到显示设备。

理解 SurfaceFlinger 的意义在于，它能将性能分析的视角从"应用画得慢不慢"提升到"整条图形管线的哪个环节出了问题"。很多时候 App 渲染没问题，但用户还是觉得卡——这种问题的根因往往在 SurfaceFlinger 这一层。可能是合成耗时过长，可能是 VSync 信号分发有延迟，也可能是 BufferQueue 的 Buffer 周转不过来。

在 Perfetto 中，SurfaceFlinger 的相关 Track 包括：SurfaceFlinger 主线程（展示合成各阶段耗时）、VSYNC-sf（触发合成的信号）、VSYNC-app（触发渲染的信号）、以及 BufferQueue 系列操作（dequeueBuffer、queueBuffer、acquireBuffer、releaseBuffer）。下面先从 SurfaceFlinger 本身的工作机制说起，这些 Track 的含义会在后续 Perfetto 部分逐一说明。

## 核心机制：Layer 合成、VSync 分发与 Buffer 管理

SurfaceFlinger 是 Android 系统中唯一能够直接修改显示内容的核心服务，运行在独立的系统进程中。它的核心职责可以归纳为三件事：管理 Layer 并将它们合成为最终画面、分发 VSync 信号驱动渲染管线、以及通过 BufferQueue 管理数据流转。

### Layer 合成：多源汇聚为一帧

一个典型的前台界面，至少会同时出现几个 Layer：屏幕顶部的状态栏、底部或侧面的导航栏，以及应用自身的界面。每个 Layer 都可以独立更新，比如状态栏显示时间变化时，只需要刷新自己的 Layer，不需要整个屏幕一起重绘。

当 VSYNC 信号到达时，SurfaceFlinger 会遍历它的 Layer 列表，检查每个 Layer 是否有新的 Buffer。如果找到了新 Buffer，就获取（acquire）它；如果没有新 Buffer，就继续使用上一次获取的旧 Buffer。然后 SurfaceFlinger 把所有可见的 Layer 按照 z-order 从后往前叠加，合成为一帧完整的画面，交给显示硬件呈现。

[图：SurfaceFlinger Layer 合成架构图——多个 App 的 BufferQueue 汇聚到 SurfaceFlinger，SurfaceFlinger 按 z-order 叠加后输出到 Display]

### VSync 分发：管线的节拍器

SurfaceFlinger 既负责合成画面，也参与软件 VSync 的调度。硬件 VSync 仍由 HWC（Hardware Composer）提供，但 Android 12 之后不能简单写成“DispSync 被 VsyncModulator 替换”。在 `android-14.0.0_r1` 的 `Scheduler::createEventThread()` 里，系统仍然为 `app` 和 `appSf` 创建 EventThread 连接，它们共用 `getVsyncSchedule()` 计算软件 VSync；`Scheduler::onFrameSignal()` 再把 `sf-vsync` 送进合成入口。`VsyncModulator` 负责 phase 调整，例如事务提交和刷新率切换时修改 app / sf 的 offset；完整分发路径还包括 EventThread、VSync Dispatch 和 Scheduler。

- **VSYNC-app**：发给应用进程，触发 Choreographer 开始一帧的 `measure → layout → draw`。
- **VSYNC-sf**：发给 SurfaceFlinger，触发本帧的事务整理、Buffer 获取和合成。

工程上更稳妥的理解是，`Scheduler`、`EventThread`、`VSync Schedule` 负责生成并投递软件 VSync，`VsyncModulator` 负责在特殊时刻调整 phase。我们在 §2.3 中单独展开 offset 的计算，SurfaceFlinger 能不能在合适的时刻拿到 Buffer，取决于 `VSYNC-app` 和 `VSYNC-sf` 的相对 phase 是否稳定。

### Buffer 管理：BufferQueue 的四步流转

SurfaceFlinger 和应用之间通过 BufferQueue 传递画面数据。最常见的状态变化有四步，但它们描述的是一个 Buffer 如何在 producer 和 consumer 之间周转，不能把它理解成“同一帧一定在一个 VSync 周期里完成完整往返”：

1. **dequeueBuffer（App 发起）**：App 从 BufferQueue 申请一块当前可写的 `GraphicBuffer`，准备用来绘制下一帧。
2. **queueBuffer（App 发起）**：App 完成渲染后，把这个 Buffer 连同 acquire fence 交回队列，通知 consumer 有新内容可取。
3. **acquireBuffer（SurfaceFlinger 发起）**：SurfaceFlinger 在合适的 latch 时机取出最新可用 Buffer，准备参与本帧合成。
4. **releaseBuffer（SurfaceFlinger 发起）**：这一帧完成 present 之后，consumer 通过 release fence 告诉 producer 这个 Buffer 何时可以再次复用。

读 Trace 时要把 `queueBuffer()` 和“Buffer 已经可复用”分开看。`queueBuffer()` 只是把新内容送进队列，SurfaceFlinger 往往要等下一次 `VSYNC-sf` 或后续一次 latch 才会 `acquireBuffer()`；Buffer 真正回到空闲池，还要等显示侧消费完成、release fence signal、然后再执行 `releaseBuffer()`。三缓冲、`max acquired buffer count`、以及 HWC 持有 Buffer 的时长，会一起决定这条流水线能压多深。想把 backpressure 看明白，最好把本节和 §2.13 BufferQueue、§2.16 Sync Fence 一起读。

[图：Perfetto 对照示意。上方是应用进程中的 dequeueBuffer 和 queueBuffer，下方是 surfaceflinger 进程中的 acquireBuffer 和 releaseBuffer，旁边再标出 VSYNC-sf。正常节奏下，queueBuffer 出现在应用完成 GPU 渲染之后，acquireBuffer 通常跟在下一次或后续一次 VSYNC-sf 的 latch 之后，releaseBuffer 要等 present 完成并且 release fence signal，Buffer 才能重新进入空闲池。]

### SF 慢 → dequeueBuffer 阻塞：backpressure 的完整路径

SurfaceFlinger 合成慢不只是自己的问题——它会沿着 BufferQueue 链向上传递 backpressure，最终堵死 App 的渲染线程。

这条路径发生在 consumer 释放旧 Buffer 与 producer 重新拿到可写 slot 之间（已验证 AOSP `BufferQueue Producer.cpp` 行 297–399、`BufferQueue Consumer.cpp` 行 480–591）：SurfaceFlinger / HWC 持有 Buffer 参与合成或等待 present fence 时，consumer 侧 `releaseBuffer()` 还没有让对应 slot 回到可用状态；App 的 RenderThread 调用 `dequeueBuffer()` 后，会在 `waitForFreeSlotThenRelock()` 里等待 free slot、out fence 或 release fence 条件满足，必要时进入 `mDequeueCondition.wait(lock)`。当 consumer 完成 release 并触发 `mDequeueCondition.notify_all()` 后，producer 才能继续拿到可写 Buffer。

在 Trace 里看到 RenderThread `dequeueBuffer()` 阻塞，根因不一定在 App 侧。顺着往上看：如果 SurfaceFlinger 主线程的 `commit` / `composite` / `present` 耗时异常，或者 HWC 持有 Buffer 时间变长，`dequeueBuffer()` 等待通常是下游长期持有 Buffer 的结果。反过来，如果 SurfaceFlinger 并不忙，但 dequeue 依然持续阻塞，那就该查 slot 数量配置、shared buffer mode、或 buffer count 约束这些上层设置。

[已验证：AOSP android-main `BufferQueue Producer::waitForFreeSlotThenRelock`、`BufferQueue Consumer::releaseBuffer::mDequeueCondition.notify_all`]

## 合成方式：Client 合成与 Device 合成

SurfaceFlinger 有两种合成方式：Client 合成（也叫 GPU 合成）和 Device 合成（也叫 HWC 硬件合成）。区分两者，才能读懂合成耗时和功耗变化。

### Client 合成：GPU 走一遍完整渲染流程

当 SurfaceFlinger 决定使用 Client 合成时，它会通过 RenderEngine（底层使用 OpenGL ES 或 Vulkan）将所有需要合成的 Layer 按顺序渲染到一个 Framebuffer 目标上。这可以视作一次特殊的渲染 Pass。SurfaceFlinger 充当 GPU 客户端，把每个 Layer 当作一个纹理，设置好变换参数和混合模式，然后逐层绘制。

Client 合成的优势在于灵活性——GPU 能处理任何复杂的变换、缩放、旋转和混合效果。但代价也很明显：它需要占用 GPU 算力，消耗额外的内存带宽，并且整个合成过程是"实打实的渲染"，需要等待 GPU 完成。当 Layer 数量多或者 Layer 内容复杂时，Client 合成的耗时可能达到好几毫秒，直接挤占 App 可用的 GPU 时间，导致 App 渲染变慢。

### Device 合成：HWC 负责把可交给显示硬件的 Layer 留在硬件路径上

HWC（Hardware Composer）在 Android 里表示 SurfaceFlinger 与厂商显示栈之间的 HAL / vendor composer 实现，边界在系统合成器和厂商显示实现之间；显示控制器里的硬件单元通常是 DPU / display controller。SurfaceFlinger 把每个 Layer 的 buffer、fence、dataspace、transform、blend、crop、z-order、composition type 等状态提交给 HWC；HWC 根据 DPU / display controller 的 overlay plane 数量、缩放、旋转、格式、保护内容、HDR / color transform 等能力，返回哪些 Layer 可以走 DEVICE composition，哪些必须回到 CLIENT composition。

执行 overlay、scanout 和显示时序控制的是 DPU / display controller 等硬件。HWC 的职责是把 Android 的 Layer 模型翻译成厂商显示硬件能接受的配置，并把 present fence / release fence 等同步结果返回给 SurfaceFlinger。Device composition 通常减少 GPU 负载和内存带宽，但 HWC HAL 调用也可能被 vendor composer、fence 等待或显示硬件状态拖长，不能把它理解成“零成本”。

不过 HWC 也有其限制。Overlay plane 数量、缩放能力、旋转支持和颜色格式约束都强依赖 SoC 的 DPU 实现，不能把某台设备的 4 个、8 个或 16 个 plane 当成通用基线。排查时以 `dumpsys SurfaceFlinger`、厂商显示文档和实际 Trace 为准；一旦超出设备能力，相关 Layer 就会退回 Client 合成。

[待验证] Android 16 HWC 3 V4 是否强制通过 `DisplayLuts` 接口下发 HDR 色调映射查找表，当前在 AOSP `android-16.0.0_r1` 的 `composer3/DisplayCommand.aidl` 与 `Composition.aidl` 中未找到 `DisplayLuts` 接口定义。HDR 合成链路中，tone mapping 可能仍依赖软件库（如 libui 中的 Skia 路径）在 GPU client 合成阶段做色彩空间转换。排查 HDR 相关合成耗时异常时，先通过 `dumpsys SurfaceFlinger` 和 vendor composer 日志确认当前设备走的是软件 tone mapping 还是硬件 LUT 路径，再针对性分析。

### 合成方式的选择逻辑

SurfaceFlinger 与 HWC 的协商可以按这条路径读：

1. SurfaceFlinger 先通过一组 `setLayer*` 调用把 Layer 的 buffer、acquire fence、z-order、visible region、dataspace、blend mode、transform 等状态写给 HWC。
2. `validateDisplay()` 让 HWC 根据本轮 Layer 组合和显示硬件能力重新计算 composition type。HWC 会返回 changed composition types 和 display requests，典型结果是某些 Layer 从 DEVICE 改成 CLIENT，或者要求 client target 参与合成。
3. SurfaceFlinger 读取 `getChangedCompositionTypes()` / `getDisplayRequests()`。需要 CLIENT composition 的 Layer 会先由 RenderEngine 合成到 client target buffer，再把这个中间结果作为一个 Layer 交回 HWC。
4. SurfaceFlinger 调用 `acceptDisplayChanges()` 接受本轮 HWC 决策，随后进入 `presentDisplay()`；部分实现支持 `presentOrValidateDisplay()`，可在一次调用里完成 present 或回退到 validate。
5. HWC 返回 present fence，SurfaceFlinger 再根据 release fence 管理前一批 buffer 的复用。

[待验证] 正文此前描述了 Android 16 AIDL Composer V4 引入 `CLIENT_BYPASS` 模式，但在 AOSP `android.hardware.graphics.composer3.Composition` 枚举中只有 INVALID / CLIENT / DEVICE / SOLID_COLOR / CURSOR / SIDEBAND / DISPLAY_DECORATION 等类型，未找到 `CLIENT_BYPASS`。该 composition type 可能来自厂商私有扩展而非 AOSP 公开接口。排查时以 `dumpsys SurfaceFlinger` 实际输出的 composition type 为准；如果某设备确实出现了 `CLIENT_BYPASS`，应标注为 vendor-specific 并给出设备/日志证据。

Android 12-16 都能按这组阶段理解，只是接口承载形式不同：Android 12 常见 HIDL composer@2.x，Android 13 起 AIDL `android.hardware.graphics.composer3` 进入主线。读 `dumpsys SurfaceFlinger`、vendor composer 日志或 Perfetto 时，Device / Client composition 要放回这组协商步骤里判断。

[图：Client 合成 vs Device 合成的架构对比——混合模式下部分 Layer 走 GPU 合成到中间 Buffer，再与 HWC 叠加层一起输出到 Display]

## SurfaceFlinger 主循环

SurfaceFlinger 的三大职责落到每一帧里，重点是版本边界：Android 12 的 `INVALIDATE / REFRESH` 与 Android 13 之后的 `commit() / composite()` 不能混成一套代码路径。

### Android 12：INVALIDATE / REFRESH

`android-12.0.0_r1` 里，SurfaceFlinger 主线程收到 VSync 后，会在 `SurfaceFlinger::onMessageReceived()` 中处理 `INVALIDATE` 和 `REFRESH` 两类消息：

```cpp
// frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp
// @ AOSP android-12.0.0_r1
void SurfaceFlinger::onMessageReceived(int32_t what, int64_t vsyncId,
                                       nsecs_t expectedVSyncTime) {
    switch (what) {
        case MessageQueue::INVALIDATE: {
            onMessageInvalidate(vsyncId, expectedVSyncTime);
            break;
        }
        case MessageQueue::REFRESH: {
            onMessageRefresh();
            break;
        }
    }
}
```

这套模型里，`INVALIDATE` 负责把“这一帧有哪些内容变了”收拢起来。它会处理事务、检查新的 Buffer、更新可见区域和脏区。`REFRESH` 再根据这些结果组织本帧的合成，决定哪些 Layer 交给 HWC，哪些 Layer 交给 RenderEngine。

如果你在旧 Trace 或旧博客里看到 `handleMessageInvalidate`、`onMessageRefresh`、`INVALIDATE`、`REFRESH` 这些 slice，它们描述的就是 Android 12 这套主线程消息模型。

### Android 13+：commit() / composite()

Android 13 起，主循环入口已从 `onMessageReceived()` 切换到 `commit()` / `composite()` 模型。`android-13.0.0_r1` 的 `MessageQueue::Handler::handleMessage()` 直接调用 `commit()` → `composite()` → `sample()`；`android-14.0.0_r1` 进一步收束到 `Scheduler::onFrameSignal()`，调度器在收到一帧信号后，先调 `commit()`，再调 `composite()`：

```cpp
// frameworks/native/services/surfaceflinger/Scheduler/Scheduler.cpp
// @ AOSP android-14.0.0_r1
void Scheduler::onFrameSignal(ICompositor& compositor, VsyncId vsyncId,
                              TimePoint expectedVsyncTime) {
    const TimePoint frameTime = SchedulerClock::now();

    if (!compositor.commit(frameTime, vsyncId, expectedVsyncTime)) {
        return;
    }

    compositor.composite(frameTime, vsyncId);
    compositor.sample();
}
```

`android-13.0.0_r1` 的 `SurfaceFlinger::commit()` 和 `SurfaceFlinger::composite()` 已不再走旧版 `onMessageReceived()`；`android-14.0.0_r1` 的签名扩展为 `SurfaceFlinger::commit(TimePoint, VsyncId, TimePoint)` 和 `SurfaceFlinger::composite(TimePoint, VsyncId)`。到 `android-16.0.0_r1`，这两个阶段继续保留，只是签名扩展成多显示场景使用的 `PhysicalDisplayId`、`FrameTargets` 和 `FrameTargeters`。

Pacesetter Display 调度在 Android 14 已出现（`android-14.0.0_r1`），`FrameTargeter` 与 `commit(PhysicalDisplayId, FrameTargets)` / `composite(...FrameTargeters)` 主签名在 Android 15 起进入主路径，Android 16 继续沿用并调整。每个物理屏幕拥有独立的 `FrameTargeter`，各自计算 VSync ID 和 present 截止时间。在多显示器场景下（外接显示器 + 内屏、桌面模式），每个 display 拥有自己的 `FrameTargeter`，独立追踪 VSync 时序和 Buffer latch 进度，不再共享单一时钟基准。SurfaceFlinger 在一次 `commit()` 中为多个 display 分别完成 latch 和合成决策，`composite()` 仍是一次调用收集多个 output 后统一进入 `mCompositionEngine->present(refreshArgs)`，当前版本未见到按 display 并行触发的 AOSP 主路径。在 Perfetto 中，多屏设备能看到 SurfaceFlinger 主线程上按 display 区分的 commit/composite slice，外接屏的帧节奏可能与内屏不同步——这是 Pacesetter 架构的设计意图，不是异常。排查多屏掉帧时，要先按 display 隔离再分析。

读代码和读 Trace 时，可以先建立一组近似关系：`commit()` 更接近旧版 `INVALIDATE` 的职责，负责收事务、latch Buffer、更新本帧状态；`composite()` 更接近旧版 `REFRESH` 的职责，负责组织合成并提交到显示设备。这样对照 Android 12 到 Android 16 的资料时，不会把不同版本的入口混成一条线。

在 Perfetto 中，旧版本更容易看到 `INVALIDATE / REFRESH` 这组 slice；新版本更适合直接盯 `commit`、`composite`、`present` 这一组阶段。无论名称怎么变，分析重点没变：本帧什么时候拿到了新 Buffer，合成决策花了多久，合成阶段是否跨过当前 VSync 窗口。

[图：SurfaceFlinger 主循环时序图，左侧是 Android 12 的 INVALIDATE / REFRESH，两步模型；右侧是 Android 13+ 的 commit / composite，两步模型。两侧都标出 VSYNC-sf 到来、Buffer latch、合成决策、present 提交四个观察点。]

## 在 Perfetto 中的表现

做性能分析时，常见任务是在 Trace 里判断 SurfaceFlinger 什么时候开始异常、异常落在哪个阶段。这一节对照 Perfetto 的 Track，把 SurfaceFlinger 的工作过程映射到界面上能直接看到的东西。

### SurfaceFlinger 主线程 Track

在 Perfetto 中展开 `surfaceflinger` 进程，主线程 Track 上最先要看的是本帧主循环的阶段名。这里同样要按版本读。

- **Android 12**：更常见的是 `INVALIDATE` 和 `REFRESH`。`INVALIDATE` 对应事务处理、Buffer 检查、脏区收敛；`REFRESH` 对应合成与 present。
- **Android 13+**：更适合直接看 `commit`、`composite`、`present` 这一组 slice。名称变了，分析思路没有变，仍然是先看本帧是否 latch 到新内容，再看合成阶段是否超时。

**正常表现**：不论 slice 名称是哪一组，总耗时都应该稳定落在当前刷新周期内。60Hz 设备的预算约 16.67ms，120Hz 设备约 8.33ms，SurfaceFlinger 自身通常只占其中一部分。

**异常表现**：如果 `REFRESH` 或 `composite` 突然拉长，先检查 Client 合成比例是否上升、Layer 数量是否突增，或者 GPU 是否被 App 侧任务占满。如果 `INVALIDATE` 或 `commit` 明显变长，优先怀疑事务量、窗口几何变化、Buffer latch 迟到，或者主线程被长事务阻塞。

### VSYNC-sf Track

这个 Track 显示触发 SurfaceFlinger 合成的 VSync 信号时间点。在 Perfetto 中它表现为一系列等间距的竖线（60Hz 设备间距约 16.67ms，120Hz 设备约 8.33ms）。每次 VSYNC-sf 到来后，SurfaceFlinger 主线程 Track 上应紧跟着出现对应的合成工作。

**正常表现**：VSYNC-sf 信号均匀分布，SurfaceFlinger 在每个信号后立即开始工作。

**异常表现**：如果 VSYNC-sf 信号的间距不均匀（有跳变），说明 VSync 偏移（offset）可能被动态调整了，或者硬件 VSync 本身有抖动。如果 SurfaceFlinger 没有在 VSYNC-sf 后及时开始工作，说明主线程有阻塞。

### VSYNC-app Track

这个 Track 显示触发应用程序渲染的 VSync 信号。VSYNC-app 和 VSYNC-sf 之间的时间差就是 offset——VSYNC-app 先到，App 开始渲染；渲染完成后 VSYNC-sf 到来，SurfaceFlinger 开始合成。

**检查点**：VSYNC-app 到 VSYNC-sf 的间距应该稳定。间距缩短会压缩 App 在本轮 SF latch 前的生产时间，`doFrame`、RenderThread 渲染或 GPU fence 稍有延迟就更容易错过 latch。间距增大通常给 App 更多生产时间，但会改变 SF / display 侧余量和端到端延迟，仍要结合 expected present、actual present 和 FrameTimeline 判断。

### BufferQueue Track

BufferQueue 的四步操作在 Perfetto 中可以分别追踪：

- **dequeueBuffer**：出现在 App 进程中。App 请求一块空闲 Buffer。如果这里阻塞，先检查空闲 Buffer 数量是否不足，或者前一批 Buffer 的 release fence 是否还没 signal。
- **queueBuffer**：出现在 App 进程中。App 完成渲染后提交 Buffer。queue 之后并不等于“这一帧马上就会被显示”，它只是进入 consumer 等待队列。
- **acquireBuffer**：出现在 SurfaceFlinger 进程中。SurfaceFlinger 在本帧 latch 时取出一个可用 Buffer。三缓冲下，`queueBuffer()` 与 `acquireBuffer()` 之间跨一帧是正常现象。
- **releaseBuffer**：出现在 SurfaceFlinger 进程中。只有 consumer 不再持有这个 Buffer，且 release fence 已经满足复用条件，producer 侧才能再次把它 dequeue 回去。

**正常流转**：dequeue → 渲染 → queue 之后，Buffer 进入等待 latch 的队列；SurfaceFlinger 在后续某次 `VSYNC-sf` 中 acquire；present 完成后再 release。三缓冲 trace 里，经常能看到应用正在绘制 frame N，而 SurfaceFlinger 此时释放的是 frame N-2 或 N-3 的 Buffer，这属于正常流水线深度。

**异常标志**：
- dequeueBuffer 明显阻塞：空闲 Buffer 不够用。根因可能是 `max acquired buffer count` 已满、release fence 迟迟没有 signal，或者 HWC / SurfaceFlinger 持有 Buffer 时间过长。
- queueBuffer 之后连续多个 `VSYNC-sf` 都没有对应的 acquireBuffer：说明这块 Buffer 没有按预期在下一轮 latch，被跳帧、旧 Buffer 复用或 consumer 时序拖慢。
- releaseBuffer 一直推迟：要继续看 present 阶段、FrameTimeline 和 fence 状态，确认是 SurfaceFlinger 合成慢，还是显示硬件扫描输出仍在持有这个 Buffer。

### HWC 合成 Track

SurfaceFlinger 与 HWC 的通信过程也可以在 Trace 中追踪。在 SurfaceFlinger 主线程 Track 上，`prepareFrame` 和 `doComposition` 阶段会包含与 HWC 的交互。

**Device 合成（HWC Overlay）**：当 Layer 走 HWC 硬件合成时，Perfetto 中能直接看到的是 SurfaceFlinger 调用 HWC、提交 present、等待 fence 的时间；overlay 混合与 scanout 发生在显示硬件中，Perfetto 无法直接展开 vendor composer 内部和 DPU 处理细节。参考设备上的 `doComposition` / present 相关 slice 往往较短，但不能写死成固定的 1ms 门槛。某些设备上，HWC HAL 调用、present fence 或 release fence 等待也会把 display 侧时间拉长。

**Client 合成（GPU/RenderEngine）**：当某些 Layer 退回 GPU 合成时，`doComposition` 切片会明显变长。能看到 RenderEngine 相关的 GPU 操作耗时，这是 SurfaceFlinger 作为 GPU 客户端执行渲染 pass 的时间。如果 Client 合成的 Layer 较多或内容复杂，这个耗时可能占掉当前刷新周期里很大一段预算，反映在 SurfaceFlinger 主线程的 `REFRESH` / `composite` 总耗时中。

**排查要点**：在 Trace 中发现 SurfaceFlinger 的 `doComposition` 或 `composite` 突然耗时增加时，先确认 Layer 是否从 DEVICE 退回 CLIENT，再看 HWC HAL 调用和 fence 是否存在等待。可以通过 `dumpsys SurfaceFlinger` 的 Layer / Display / HWC 状态、Perfetto 的 FrameTimeline 和 vendor composer 日志，把 SF 调用耗时、GPU client 合成耗时、present fence 延迟分开判断。

[图：Perfetto 对照示意。左侧是 Device Composition 场景，`doComposition` slice 很短，FrameTimeline 按预期 present；右侧是某个 Layer 因缩放、裁剪或特效退回 Client Composition 后，`doComposition` 明显拉长，RenderEngine 相关工作与 GPU 负载重叠，最终出现 delayed present。]

### 正常 vs 异常：一个对比案例

**正常场景**：App 渲染耗时 5ms → queueBuffer → VSYNC-sf 到来 → SurfaceFlinger acquireBuffer + 合成耗时 3ms → 提交给 HWC → 下一帧正常呈现。整个 Trace 看起来节奏均匀，没有任何一个环节拖后腿。

**异常场景**：App 渲染正常（5ms），但 SurfaceFlinger 的 `doComposition` 突然耗时 12ms（可能因为某个 Layer 的缩放操作触发了 Client 合成，而 GPU 正忙于其他任务）。结果 SurfaceFlinger 没能在当前 VSync 周期内完成合成，导致这一帧被延迟到下一个 VSync 才呈现——用户感知到一次卡顿。在 Trace 中，SurfaceFlinger 主线程 Track 上会出现一个明显拉长的 doComposition 切片，紧接着下一帧的 VSYNC-sf 没有触发合成（因为上一帧还没处理完），这就是典型的"SF 导致的全局掉帧"。

## Layer 与 z-order

前面多次提到 Layer 和 z-order，这里展开讲讲。

Layer 是 SurfaceFlinger 管理显示内容的基本单元。每个 Activity、每个 Window、每个 Surface 都对应一个 Layer。在 SurfaceFlinger 眼里，屏幕上的一切都是 Layer 的叠加——状态栏是一个 Layer，导航栏是一个 Layer，App 界面是一个 Layer，浮动通知也是一个 Layer。

Layer 之间有父子关系，构成树形结构。父 Layer 可以控制子 Layer 的可见性和变换。最终决定屏幕上显示效果的是 z-order——Layer 的前后顺序。z-order 值越大的 Layer 越靠前（离用户越近），会遮挡 z-order 值小的 Layer。

Android 12-16 的 SurfaceFlinger 主路径不要再按旧博客中 Layer stack 重建 / working set 两个阶段名解释。更稳妥的口径是：`SurfaceFlinger::commit()` 收拢 transaction、Layer state 和 Buffer latch 结果；`SurfaceFlinger::composite()` 把可见 Layer 交给 CompositionEngine；CompositionEngine 的 Output / OutputLayer 路径再按显示输出计算可见区域、裁剪、z-order、composition type，并把结果送往 HWC 或 RenderEngine。通过 `dumpsys SurfaceFlinger` 可以查看当前 Layer 树、z-order、Buffer 状态和部分合成类型快照。

一个常见的性能陷阱是可见 Layer 数量过多。每多一个可见 Layer，SurfaceFlinger 在 commit/composite 与 CompositionEngine 输出规划中就要多处理一份状态，HWC 也要评估是否还能分配 overlay plane。当 Layer 组合超过 DPU / display controller 能力，或存在缩放、旋转、透明、颜色格式等限制时，部分 Layer 会退回 Client 合成，GPU 和内存带宽开销会上升。减少不必要的 Surface / 硬件层、控制窗口和浮层数量，是排查这类问题时的基础动作。

[图：Layer 树形结构和 z-order 排列示意图——状态栏(z=高)、App(z=中)、壁纸(z=低)的叠加关系]

## Jank 与 SurfaceFlinger 的关系

SurfaceFlinger 的性能问题会表现成系统级卡顿。因为 SurfaceFlinger 是全局合成器，它的主线程卡顿会影响所有可见的应用。

具体来说，如果 SurfaceFlinger 在某一帧的事务处理或合成过程中耗时过长，会发生以下连锁反应：

1. 这一帧来不及在当前 VSync 窗口内完成 latch、composite 或 present，被推迟到后续一次显示周期。
2. 所有 App 的最新渲染结果都不会在当前帧呈现，即使 App 侧已经按时 `queueBuffer()`。
3. SurfaceFlinger 或 HWC 持有已 acquire 的 Buffer 更久，release fence 更晚 signal，producer 可复用的 Buffer 数量减少。
4. 如果 BufferQueue 已经接近 `max acquired buffer count`，后续 `dequeueBuffer()` 就会阻塞；如果三缓冲里暂时还有空闲 Buffer，阻塞可能延后一两帧才出现。

在 Perfetto 中，这种情况表现为：SurfaceFlinger 主线程 Track 上出现一个明显拉长的合成切片，紧接着几个 VSYNC-sf 信号都没有触发合成（因为上一帧还在处理），然后 SurfaceFlinger 追赶式地处理积压的帧。在用户侧，这就是一段明显的卡顿。

我们在实际分析中，最常遇到的 SurfaceFlinger 卡顿原因有四类。

第一类是**Layer 数量突增**。比如进入多窗口模式或弹出系统 Dialog，合成工作量显著增加。第二类是**Client 合成比例增大**。某些 Layer 的属性发生变化后，HWC 无法处理，系统只能退回 GPU 合成，GPU 渲染耗时会明显上升。第三类是**GPU 争抢**：App 的渲染任务和 SurfaceFlinger 的 Client 合成任务共享 GPU，当 App 侧的 GPU 负载很高时，SurfaceFlinger 的合成也会被拖慢。第四类是**Transaction 风暴**。大量 Layer 状态更新会把事务处理阶段拉长，Android 12 常表现为 `handleMessageTransaction` / `INVALIDATE` 相关 slice 变长，Android 14+ 更常见的是 `commit` 阶段里的事务处理时间增加。

应对思路也很直接：减少 Layer 数量、尽量让更多 Layer 走 HWC 合成、控制 Transaction 的频率和数据量。具体的排查方法论，我们在 §7.3（卡顿分析方法论）中会系统讲解。

## Blast BufferQueue

本节聚焦 Android 12-16，但主窗口 BLAST 进入主线的时间点要往前挪到 Android 11。Android 11 的 `ViewRootImpl` 已经把主窗口 Buffer 提交和 `SurfaceControl.Transaction` 绑定到 BLAST 路径里；Android 12 之后，这套路径再和 FrameTimeline、窗口同步分析口径一起变得更容易观测。

### Android 11：主窗口 BLAST 进入主线

Legacy 模型里，Buffer 通过 BufferQueue 在 producer 和 consumer 之间流转，窗口大小、裁剪、位置这类几何信息则通过 `SurfaceControl.Transaction` 单独提交。窗口 resize、旋转、分屏切换、IME 顶起这类场景里，二者如果落在不同的 frame boundary，上层就可能看到内容已经换成新 Buffer，几何信息却还是旧状态，表现为 stretch、jump 或短暂不同步。

Android 11 把主窗口 BLAST 放进 `ViewRootImpl` 主线后，应用侧会在 `BLAST BufferQueue` 中先取到待提交 Buffer，再把 Buffer、fence 和几何 transaction 合成一笔 `SurfaceControl.Transaction` 送给 SurfaceFlinger。这条路径解决的是“同一帧里内容和壳子怎么一起到位”的问题。

### Android 12+：分析口径更完整

Android 12 没有“才引入 BLAST”，它做的是把既有 BLAST 路径和 FrameTimeline、VSync Id、窗口同步分析口径更紧地绑在一起。做 Perfetto 分析时，Android 12+ 更容易把 Buffer 提交、transaction 应用、expected present 和 actual present 放到同一组观察点里。

### 代码锚点与 transaction 合并顺序

主窗口侧入口在 `frameworks/base/core/java/android/view/ViewRootImpl.java`。一次 draw 完成后，ViewRootImpl 会把新 Buffer 的提交与本轮窗口几何、裁剪、位置、大小等 `SurfaceControl.Transaction` 组织到同一帧边界上。native 侧对应 `frameworks/native/libs/gui/BLASTBufferQueue.cpp`：

1. `BLAST BufferQueue::onFrameAvailable()` 收到 producer queue 进来的 `BufferItem`，进入 `acquireNextBufferLocked()`。
2. `acquireNextBufferLocked()` 取出 buffer、acquire fence、dataspace、surface damage、transform、crop、frame number 等元数据。
3. BLAST 创建或复用一笔 `SurfaceComposerClient::Transaction`，通过 `Transaction::setBuffer()` 绑定 buffer 和 acquire fence，并继续写入 `setDataspace()`、`setSurfaceDamageRegion()`、frame number / desired present time 等帧属性。
4. 如果同一帧还有 ViewRootImpl 侧的 geometry transaction，BLAST 会把内容 buffer transaction 与 geometry / sync transaction 合并后提交，避免“新内容 + 旧壳子”或“旧内容 + 新壳子”跨帧出现。
5. Android 13+ 的 `SurfaceFlinger::commit()` 阶段消费这笔 transaction，完成 Layer 状态更新、buffer latch 和 frame timeline 归因；后续 `composite()` 再按 HWC / RenderEngine 决策进入显示。

读 Trace 时，把 BLAST 当成“BufferQueue + 同帧 SurfaceControl.Transaction 提交”这层适配即可。如果某一帧同时发生 Buffer 更新和 geometry 变化，检查它们是否落在同一个 frame number / VSync Id 上。consumer、fence 和 release 链仍然存在；释放阶段还会走 `releaseBufferCallbackLocked()`，最终回到 `mBufferItemConsumer->releaseBuffer()`。这部分可和 §2.13 BufferQueue、§2.16 Sync Fence 一起读。

## 与其他机制的关系

SurfaceFlinger 位于 App（producer）、HWC 和显示硬件之间：

- **VSync 机制（§2.3）**：VSYNC-sf 信号驱动 SurfaceFlinger 的合成时机，VSYNC-app 信号驱动 App 的渲染时机。两个信号的 offset 配置直接决定了整条管线的效率。
- **Choreographer（§2.4）**：Choreographer 在收到 VSYNC-app 后调度 App 的 measure/layout/draw 工作。App 渲染完的 Buffer 通过 BufferQueue 提交给 SurfaceFlinger。如果 App 端的 Choreographer 回调执行太慢，Buffer 就来不及在下一个 VSYNC-sf 前准备好。
- **RenderThread（§2.5）**：App 的 RenderThread 负责将绘制命令提交给 GPU 执行。GPU 渲染完成后，RenderThread 调用 queueBuffer 提交结果。如果 GPU 渲染慢，queueBuffer 会延迟，SurfaceFlinger 在 VSYNC-sf 时就取不到新 Buffer。

整条管线的时序关系是：VSYNC-app → Choreographer.doFrame → RenderThread 渲染 → queueBuffer → VSYNC-sf → SurfaceFlinger 合成 → 提交显示。任何一个环节慢了，最终的帧呈现都会延迟。

## 版本演进

SurfaceFlinger 的主干职责没有变，变化主要发生在调度入口、Buffer 提交方式，以及 HWC / RenderEngine 的接口演进上。

**Android 4.1（Project Butter）**：引入 VSync 同步、三缓冲和更成体系的 HWC 协同，这是 SurfaceFlinger 现代调度模型的起点。

**Android 7.0**：HWC 2.0 接口成熟，`prepare()/set()` 演进为 `validate()/present()`，HDR、color transform matrix 等能力开始纳入统一接口。Nougat 这一版的另一个系统级变化是 mediaserver 拆分，SurfaceFlinger 在更早版本就已经是独立的系统合成服务。 [已验证：AOSP + source.android.com HWC 文档]

**Android 8.0（Project Treble）**：HWC HAL 迁移到 HIDL 接口（`android.hardware.graphics.composer@2.1` 到 `@2.4`），SurfaceFlinger 通过稳定 HAL 边界与厂商实现交互。

**Android 10**：围绕帧统计、present fence 和合成观测的能力继续完善，SurfaceFlinger 与性能工具能拿到的时间戳更多，但 Perfetto 中今天所说的 FrameTimeline 还没有作为完整体系出现。

**Android 11**：主窗口 BLAST 进入 `ViewRootImpl` 主线，Buffer 提交和窗口几何 transaction 开始按同帧语义组织。分析 resize、rotation、relayout 这类问题时，BLAST 已经是主路径之一。

**Android 12**：FrameTimeline 进入官方性能分析体系，BLAST 路径上的 VSync Id、expected present、actual present 更容易放到同一时间基准里观察；窗口同步和 SurfaceView 相关分析口径也更稳定。

**Android 13**：SurfaceFlinger 主循环从 `onMessageReceived()` 切换到 `commit()` / `composite()` 模型（`MessageQueue::Handler::handleMessage()` 直接调用 `commit()` → `composite()` → `sample()`）；HWC HAL 开始支持 AIDL 接口（`android.hardware.graphics.composer3` / `IComposer.aidl`），用于替代 HIDL composer。

**Android 14**：`Scheduler::onFrameSignal()` 进一步收束调度入口，`SurfaceFlinger::commit()` / `composite()` 继续作为主流程；`PROPERTY_DEBUG_RENDERENGINE_BACKEND` 已能识别 `skiavk` 和 `skiavkthreaded`，但 Vulkan backend 是否实际启用仍取决于设备配置和厂商实现。

**Android 14+**：HIDL 版 composer 2.4 被标记为 deprecated，厂商实现继续向 AIDL 收敛。

**Android 15**：ARR / 可变刷新率让 VSync 调度、present hint 和刷新率切换的关系更复杂。分析 SurfaceFlinger 时，需要结合 §2.18 / §2.19 看刷新率策略、FrameTimeline 和 present fence，不能只按固定 60Hz / 120Hz 节拍推断。

**Android 16**：`SurfaceFlinger::commit(PhysicalDisplayId, FrameTargets)` 与 `composite(PhysicalDisplayId, FrameTargeters)` 继续沿用分阶段模型，多显示 target 计算更细，入口没有回到旧版 `onMessageReceived()`。

## 几个容易混淆的边界

### App 帧按时产出，只说明 producer 侧正常

App 的 MainThread 和 RenderThread 都在预算内，只能说明 producer 侧没有拖延。SurfaceFlinger 合成、HWC present 或 release fence 回收拉长时，FrameTimeline 仍然会把这一帧记成 display 侧超时。

### SurfaceFlinger slice 变长，先查输入条件

SurfaceFlinger 的长 slice 经常是上游输入条件推高的结果，例如 Layer 数量突然增加、几何事务暴增、某个 Layer 退回 Client 合成，或者 GPU 同时被 App 渲染任务占满。排查时要把事务量、Layer 属性和 GPU 竞争一起看。

### HWC 合成通常更省 GPU，但判断要结合设备约束

Device composition 往往更省 GPU 和带宽，但前提是当前 Layer 组合没有踩中 plane 数量、缩放、旋转、颜色格式和特效限制。是否划算，要看这台设备的 DPU 能力和当时的 Layer 组合，抽象概念只能作为起点。

### `dumpsys SurfaceFlinger` 适合看快照，Perfetto 负责时序

`dumpsys SurfaceFlinger` 适合确认 Layer 树、合成类型、Buffer 状态和刷新率配置。掉帧发生时刻、Fence 等待、present 延迟和 transaction 风暴，还是要回到 Perfetto 的时间线里判断。



## HWC Overlay Plane Capability 与合成降级

### HWC2 Overlay Capability 查询机制

**源码位置**：`frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.cpp` (Android 14 tag: `android-14.0.0_r1`)

Overlay Plane 数量没有 Android 通用基线，取决于 SoC、DPU / display controller 能力、分辨率、刷新率和当前 Layer 组合。HWC2 通过 `validateDisplay()` / `presentDisplay()` 两阶段流程与 SurfaceFlinger 交互：

```cpp
// frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.cpp
// @ AOSP android-14.0.0_r1, Display::getRequests() 节选
Error Display::getRequests(HWC2::DisplayRequest* outDisplayRequests,
                           std::unordered_map<HWC2::Layer*, LayerRequest>* outLayerRequests) {
    auto intError = mComposer.getDisplayRequests(
            mId, &intDisplayRequests, &layerIds, &layerRequests);
    // layerRequests 由 HWC 返回，用于表达本轮 Layer 请求。
}
```

**Composition 类型锚点**：HIDL composer 2.1 的 `Composition` 定义在 `hardware/interfaces/graphics/composer/2.1/IComposerClient.hal`，包含 `CLIENT`、`DEVICE`、`SOLID_COLOR`、`CURSOR`、`SIDEBAND`。AIDL composer3 的定义在 `hardware/interfaces/graphics/composer/aidl/android/hardware/graphics/composer3/Composition.aidl`，继续保留这些值，并包含 `DISPLAY_DECORATION = 6`。HIDL 2.1 没有 `BACKGROUND` 或 `DISPLAY_DECORATION`，不要把 HIDL 和 AIDL 的枚举混在同一个版本锚点里。

### 合成降级的完整触发链

以下条件会触发 CLIENT 合成降级（DEVICE→CLIENT）：

1. **[硬件限制]** Layer 数量 > HWC Overlay Plane 数量
2. **[格式不支持]** Layer 像素格式不在 HWC 支持列表
3. **[混合模式]** 需要复杂 blending（SRC_OVER 等）且 HWC 不支持
4. **[旋转变换]** 旋转角度 HWC 不支持（如 90° 旋转某些 GPU 不支持）
5. **[缩放变换]** 超出 HWC 硬件缩放器范围
6. **[功耗策略]** MTK 低电量模式主动请求 CLIENT
7. **[带宽限制]** 高刷新率 + DSI/Bridge 带宽受限时 MTK 触发

### dumpsys SurfaceFlinger 中的证据

```
类型: Device
─ #0   ...  LAYER_NUMID=40001  |  HWC layer name: SurfaceView
─ #1   ...  LAYER_NUMID=40002  |  HWC layer name: Background

类型: Client
─ #2   ...  LAYER_NUMID=40003  |  HWC layer name: com.example.app/ViewGroup
```

- `类型: Device` = HWC 直接合成（Overlay Plane 处理）
- `类型: Client` = GPU 合成后提交（HWC 后处理）

**关键命令**：
```bash
dumpsys surfaceflinger          # 完整状态
dumpsys surfaceflinger layers   # Layer 详细信息
```

### 厂商差异

| SoC 系列 | 策略特征 |
|---------|---------|
| 高通 QdX | 最大化 DEVICE 合成，Video overlay 优化，120Hz 高刷优先 DEVICE |
| 联发科 MTK | 功耗优先策略，低电量请求 CLIENT，Frame Rate Migration |


## 参考资料

### AOSP 源码

- `frameworks/native/services/surfaceflinger/SurfaceFlinger.cpp` — SurfaceFlinger 主流程实现，Android 12 侧重 `onMessageReceived` / `handleMessageInvalidate` / `onMessageRefresh`，Android 13+ 侧重 `commit()` / `composite()`
- `frameworks/native/services/surfaceflinger/CompositionEngine/src/Output.cpp` / `OutputLayer.cpp` — 显示输出层规划、可见区域、裁剪和 composition type 计算入口
- `frameworks/native/services/surfaceflinger/` — SurfaceFlinger 服务完整实现
- `frameworks/base/core/java/android/view/ViewRootImpl.java` — 主窗口 BLAST 接入路径
- `frameworks/native/libs/gui/BLASTBufferQueue.cpp` — BLAST BufferQueue 实现（Android 11 进入主线，Android 12+ 更适合结合 FrameTimeline 一起分析）
- `frameworks/native/libs/gui/SurfaceComposerClient.cpp` — SurfaceControl.Transaction / SurfaceComposerClient::Transaction 的 native 实现
- `hardware/interfaces/graphics/composer/` — HWC HAL 接口定义（HIDL @2.x 和 AIDL composer3）
- `frameworks/native/libs/renderengine/` — RenderEngine 实现（OpenGL ES / Vulkan 后端）

### 官方文档

- [Android SurfaceFlinger 概述](https://source.android.com/docs/core/graphics/surfaceflinger) — 官方架构说明
- [Android 图形架构总览](https://source.android.com/docs/core/graphics/architecture) — 官方图形系统全景图
- [Hardware Composer HAL](https://source.android.com/docs/core/graphics/hwc) — HWC HAL 版本与接口说明

### 博客与文章

- [高爷 Android Performance 博客](https://www.androidperformance.com/) — SurfaceFlinger、BufferQueue、Systrace/Perfetto 分析系列



### SurfaceFlinger 事务与缓冲区生命周期（源码级调研）
- 来源：DeepResearch 调研（2026-05-29）
- 摘要：分析 SurfaceFlinger 双缓冲状态模型（mCurrentState/mDrawingState 原子更新）、MessageQueue INVALIDATE/REFRESH 双消息机制、BufferQueue 状态机完整循环（FREE→QUEUED→DEQUEUED→ACQUIRED→FREE），以及 Android 13 mScheduler 替代和 Android 17 DeliQueue 无锁 MessageQueue 重构。
- ⚠️ `android-17.0.0_r1` 公开 tag 截至 2026-06-12 尚未发布，本节不将其作为正文结论。



> Android 17 边界：截至 2026-06-12 未核到 `android-17.0.0_r1` 公开 tag；下面几条 Android 17 相关材料只作为“未进入 Android 17”的研究线索，不作为本节正文结论。

### Android 17 SurfaceFlinger LocklessQueue 与 TransactionHandler 流水线（源码级调研，2026-06-08 补完）
- 来源：DeepResearch 调研（2026-06-08）— `2026-06-08-android-17-sf-transaction-queue-lockless-architecture.md`
- 摘要：在 2026-05-29 报告（双缓冲 MessageQueue）基础上，补完 FrontEnd 重构后的事务队列与处理路径。`frameworks/native/services/surfaceflinger/LocklessQueue.h` 提供真正无锁 MPSC 队列（CAS-based push + 单消费者 pop），binder 线程事务入队不再持 `mStateLock`；`FrontEnd/TransactionHandler.h` 用双层队列（LocklessQueue + per-applyToken FIFO）配合三个 TransactionFilter 槽位完成事务批过滤；`SurfaceFlinger::setTransactionState` 与 `applyTransactionState` 通过 LocklessQueue 解耦；barrier TTL 默认 5s 防止永久卡死。⚠️ 边界说明：`android-17.0.0_r1` 公开 tag 截至 2026-06-08 尚未发布，所有"Android 17"声明均基于 android-16.0.0_r4 已就位代码的延续性推断。
- 关键调用链：`setTransactionState` → `mTransactionHandler.queueTransaction` (LocklessQueue push) → `setTransactionFlags(eTransactionFlushNeeded)` → 主线程 `flushTransactions` → `applyTransactions` → `applyTransactionsLocked` → `applyTransactionState` (持 mStateLock)。

### BufferQueue 内部锁竞争机制（源码级调研）
- 来源：DeepResearch 调研（2026-05-08）
- 摘要：详述 BufferQueue 单一 mutex + 多 condition variable 锁架构，分析 dequeueBuffer 等待、ActiveBuffer O(n) 扫描、Allocation 期间锁释放三个关键竞争路径，以及 Android 14 BUFFER_RELEASE_CHANNEL 精确唤醒优化。
### SurfaceFlinger FrontEnd 架构与 RequestedLayerState（源码级调研）
- 来源：DeepResearch 调研（2026-05-09）
- 摘要：Android 15 引入 FrontEnd 模块，将客户端请求状态（RequestedLayerState）与系统合成状态（LayerSnapshot）完全分离。通过 LayerLifecycleManager 生命周期管理和 LayerHierarchyBuilder 层级构建解耦，主合成线程只在需要合成计算时持有 mStateLock，大幅降低锁竞争。包含 Changes bitmask 枚举、TransactionHandler 事务批处理、以及 FrontEnd 目录结构。

### Android 17 SurfaceFlinger 事务与缓冲区生命周期（源码级调研）
- 来源：DeepResearch 调研（2026-05-22）
- 摘要：Android 17 SurfaceFlinger 事务与缓冲区生命周期源码分析，含双缓冲 mCurrentState/mDrawingState 原子更新机制、INVALIDATE/REFRESH 双消息分离、BufferQueue 状态机循环、Deliqueue 无锁重构 MessageQueue 优化。详述事务批处理、Buffer 获取时机、Layer 状态同步等关键路径源码实现。

