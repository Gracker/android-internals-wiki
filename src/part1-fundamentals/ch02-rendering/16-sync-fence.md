---
title: "Sync Fence 框架与帧同步机制"
chapter: "2.16"
section: "2.16"
status: ready-for-review
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
last_verified: "2026-04-11"
last_verified_against: "AOSP android-16.0.0_r1 / android-8.1.0_r81 / android-7.0.0_r1, source.android.com/docs/core/graphics/sync"
confidence: medium
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
sources:
  - type: aosp
    path: "frameworks/native/libs/ui/Fence.cpp"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.h"
  - type: aosp
    path: "system/core/libsync/sw_sync.h"
  - type: aosp
    path: "system/core/libsync/sync.c"
  - type: aosp
    path: "frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp"
  - type: official
    path: "https://source.android.com/docs/core/graphics/sync"
  - type: official
    path: "https://source.android.com/docs/core/graphics/architecture"
tags: [sync-fence, fence, hwui, rendering, synchronization, timeline]
related_chapters: ["2.4", "2.5", "2.6", "2.13", "2.15"]
pipeline_stage: task6_pending
task6_state: revisiting
task9_state: pending
task2b_state: fixed
reviewed_by: openclaw-task6
reviewed_date: "2026-04-11"
task6_result: needs-rework
task9_result: needs-rework
task2b_result: fixed
---

# 2.16 Sync Fence 框架与帧同步机制

当我们在 Perfetto 里看到 `latchBuffer`、`presentDisplay()` 或 `dequeueBuffer()` 旁边挂着一段 `fence wait` 时，真正的问题不是“这里又卡了多少毫秒”，而是“这个 buffer 现在到底归谁用，什么时候才能安全换手”。Fence 就是这条换手协议。

App、GPU、SurfaceFlinger、HWC、Display Controller 都在异步工作。App 调完 `queueBuffer()`，不等于 GPU 已经把像素写完；`presentDisplay()` 返回了，也不等于屏幕已经把这一帧真正扫上去。如果没有显式同步，系统只能靠猜时机来复用 buffer，不是撕裂，就是白等。Fence 把“还没完成但迟早会完成”的状态封装成一个可传递、可等待、可调试的 fd，于是我们才能既避免读半成品，又把等待精确归因到 producer、consumer 或 display 侧。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **Fence 为什么存在**：[已验证: source.android.com/docs/core/graphics/sync]
  显式同步解决 CPU、GPU、HWC、Display Controller 异步读写同一 buffer 的先后次序问题，避免半成品被消费，也避免靠固定 sleep 猜时机。

- 🔹 **legacy Android sync framework 与 modern sync_file API 的关系**：[已验证: AOSP android-8.1.0_r81, system/core/libsync/sync.c]
  文档里常见 `sync_timeline`、`sync_pt`、`sync_fence`，当前 userspace 更常见 `sync_file_info`、`sync_fence_info` 等 modern API。前者是理解模型和兼容层名词，后者是现代调试接口。

- 🔹 **Acquire fence、Release fence、Present fence 的方向与两侧视角**：[已验证: source.android.com/docs/core/graphics/sync, AOSP android-7.0.0_r1 HWC2.h]
  producer 在 `queueBuffer()` 输入的 fence，到了 consumer 一侧就叫 acquire fence；consumer 在 `getReleaseFences()` / `releaseBuffer()` 返回的 fence，回到 producer 下一次 `dequeueBuffer()` 时就是“写之前先等我读完”的 release fence；present fence 表示本帧真正上屏。

- 🔹 **在 Perfetto 中如何判断 fence 是正常同步还是掉帧瓶颈**：[已验证: source.android.com/docs/core/graphics/architecture]
  需要把 `queueBuffer()`、`latchBuffer`、`presentDisplay()`、BufferQueue 状态和 GPU busy 片段连起来看，不能只盯一段 `fence wait`。

- 🔹 **版本演进的真实主线**：[已验证: AOSP android-7.0.0_r1 HWC2.h, android-8.1.0_r81 system/core/libsync/sync.c, android-16.0.0_r1 SkiaOpenGLPipeline.cpp]
  Android 7 已有 HWC2；Android 8+ 用户空间已经能看到 modern libsync / sync_file API；Skia 管线在 Android 8.1 已存在，Android 14-16 的变化主要在后端调度、FrameTimeline / ARR 配合和 release fence 生成路径。

### 扩展（可选深入）

- 🔸 **sw_sync 的边界**：`sw_sync` 保留测试与特定软件管线接口，但生产路径中的 acquire / release / present fence 仍由内核驱动或硬件推进。
- 🔸 **常见误区**：fd 泄漏、slot 长时间不可复用、GPU hang 是三类不同问题，排查入口不能混用。
<!-- outline-end -->

## 为什么需要 Fence：渲染管线不是一条直线

如果没有显式同步，producer 只能靠“我猜你差不多用完了”来复用 buffer。桌面系统有时还能把这种不确定性交给单一驱动兜底，Android 不行。这里至少有 App、BufferQueue、SurfaceFlinger、HWC、Display Controller 五段链路，跨线程、跨进程、跨硬件单元是常态，任何一段快一点或慢一点，都会影响同一个 GraphicBuffer 什么时候能读、什么时候能写。

官方图形同步文档把这套机制称为 explicit synchronization。producer 把“我什么时候写完”随 buffer 一起传出去，consumer 再把“我什么时候读完”随旧 buffer 还回来。于是同样一段卡顿，我们就能继续追问：是 App/GPU 产出太慢，还是 SurfaceFlinger/HWC 长时间占着旧 buffer 不放。这个区分在 Perfetto 里非常关键，因为两类问题的优化方向完全不同。

[已验证: source.android.com/docs/core/graphics/sync]

## 核心机制：内核同步原语与 userspace 名词

Android 图形栈的同步基础来自内核里的显式同步框架。官方文档仍然用 `sync_timeline`、`sync_pt`、`sync_fence` 这组三件套解释它：`sync_timeline` 表示某个硬件上下文上的单调前进时间线，`sync_pt` 是时间线上的一个完成点，`sync_fence` 则把一个或多个完成点包装成可等待对象。这套命名很适合建立直觉，我们读内核文档和旧资料时也经常会遇到它。

但如果我们直接去读较新的 userspace 源码，会发现另一个视角更常见：`sync_file_info`、`sync_fence_info`、`sync_pt_info`。`system/core/libsync/sync.c` 在 `android-8.1.0_r81` 里已经同时包含 `legacy_sync_merge()` 和 `modern_sync_merge()`，也同时保留 `legacy_sync_fence_info()` 与 `modern_sync_file_info()`。这说明从 Android 8 开始，modern `sync_file` 风格的 userspace API 已经摆在台面上了，而 legacy 名词并没有立刻消失，它更多以兼容层和文档术语的形式继续存在。

[已验证: AOSP android-8.1.0_r81, system/core/libsync/sync.c]

| 资料里常见的名词 | 更适合的理解 |
| --- | --- |
| `sync_timeline` / `sync_pt` / `sync_fence` | legacy Android sync framework 的理解模型，也是兼容层里继续保留的命名 |
| `sync_file` / `sync_file_info` / `sync_fence_info` | modern userspace API，当前 libsync 调试与查询接口更常见 |
| `dma-fence` | 内核里的通用同步原语，驱动实现显式同步时最终落到这一层 |

把这三层拆开后，很多“资料和源码对不上”的困惑就消失了。旧文档在讲概念模型，libsync 在讲 userspace 查询接口，驱动代码则在讲内核对象本身，它们不是互相打架，而是站在不同抽象层。

### sw_sync 的边界：用户空间不是完全不能创建 fence

这一点很容易被一句话讲歪。`android-16.0.0_r1` 的 `system/core/libsync/sw_sync.h` 公开了下面三个接口：

```c
int sw_sync_timeline_create(void);
int sw_sync_timeline_inc(int fd, unsigned count);
int sw_sync_fence_create(int fd, const char *name, unsigned value);
```

这说明“用户空间完全不能创建或 signal fence”并不成立。更准确的说法是，**生产路径里的硬件 fence 由内核驱动或硬件 signal，以保证 forward progress；但 Android 同时保留 `sw_sync`，给测试和特定软件管线提供 userspace 的 software timeline 接口。** 这两件事必须分开说。

所以我们在排查图形问题时，可以把 `sw_sync` 看成测试与 fallback 工具，而不是普通 App 随手控制生产 acquire / release fence 的入口。尤其是 App 正常渲染链路里的 GPU、HWC、display fence，仍然依赖驱动与硬件推进，不靠业务进程手动 `inc`。

[已验证: AOSP android-16.0.0_r1, system/core/libsync/sw_sync.h]

## 渲染管线里的三类 Fence

先把方向钉住。Fence 的名字经常让人绕晕，不是因为系统故意复杂，而是因为**同一个 fd 从 producer 这边传到 consumer 那边，语义会跟着观察角度变化**。

```text
Producer（App / RenderThread）
  queueBuffer(buffer, fence_fd)
    └─ 这边的语义：我可能还在写这个 buffer

Consumer（SurfaceFlinger / HWC）
  收到同一个 fence_fd
    └─ 到了这边就叫 acquire fence：读之前先等 producer 写完

Consumer 完成读取后返回 release fence
Producer 下次 dequeueBuffer() 拿回旧 buffer 时收到这个 fence
  └─ 这边的语义：写之前先等 consumer 读完
```

### Producer → Consumer：`queueBuffer()` 带过去的是 consumer 侧的 acquire fence

官方同步文档写得很直白，acquire fences 会跟着输入 buffer 一起传给 `setLayerBuffer` 和 `setClientTarget`。它表示的是“这个 buffer 还有一个 pending write，没有 signal 之前别读”。所以从 producer 视角看，这个 fence 代表“我还没写完”；到了 consumer 视角，它就变成“我 acquire 这个 buffer 之前先等它写完”。

`android-7.0.0_r1` 的 HWC2 头文件已经把这件事写进接口里了：

```cpp
// frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.h
Error setBuffer(buffer_handle_t buffer,
        const android::sp<android::Fence>& acquireFence);
Error setClientTarget(buffer_handle_t target,
        const android::sp<android::Fence>& acquireFence,
        android_dataspace_t dataspace);
Error getReleaseFences(...);
Error present(android::sp<android::Fence>* outRetireFence);
```

所以把 “Android 8 才引入 HWC2” 写进版本线是不对的，Android 7 的 HWC2 接口已经明确了 acquire / release / present 这组 fence 语义。

[已验证: source.android.com/docs/core/graphics/sync, AOSP android-7.0.0_r1 HWC2.h]

### Consumer → Producer：release fence 会在下一次 `dequeueBuffer()` 前拦住写入

release fence 的方向正好相反。官方文档对它的定义是：它表示 consumer 仍在读取上一个 buffer；只有当当前 buffer 已经取代旧 buffer 上屏后，旧 buffer 对应的 release fence 才会 signal。随后这个 fence 会跟着旧 buffer 一起回到 producer，producer 在再次写这个 buffer 之前必须先等它完成。

这也是为什么我们不能把 producer 在 `queueBuffer()` 输入的那个 fence 写成 release fence。**更准确的说法是：producer `queueBuffer()` 输入的 fence，到 consumer 一侧叫 acquire fence；consumer 返回给 producer 的 fence，才是 release fence。** 两边说的是同一轮 buffer 交接的两个方向。

如果把这两个方向说反，后面分析 `dequeueBuffer()` 阻塞和 `latchBuffer` 等待时就一定会乱。一个常见误判是把 App 侧等待旧 buffer 可重用的时间，写成“等待 acquire fence”；其实它等的是 consumer 返回来的 release fence，只是 producer 拿到的字段名未必总把这个语义写在脸上。

### Present fence（旧资料里也常叫 retire fence）：本帧真正上屏的时刻

present fence 是每帧一个，它在 `presentDisplay()` 之后返回。对物理屏来说，它表示当前帧真正出现在屏幕上的时间点；对虚拟显示来说，它表示什么时候可以安全读取输出 buffer。很多旧资料会把它叫 retire fence，本质上讨论的是同一类“本帧已经完成 display 侧消费”的信号。

这条 fence 很适合用来理解端到端显示延迟。`queueBuffer()` 只能说明 producer 把帧交出来了，present fence 才更接近“用户什么时候真的看到这一帧”。如果我们在 SurfaceFlinger / HWC 侧做帧耗时分析，不把 present fence 连起来看，很容易把“已经提交”和“已经显示”混为一谈。

[已验证: source.android.com/docs/core/graphics/sync]

## 在 Perfetto 里怎么读 Fence

Fence wait 本身不是 bug。正常渲染里本来就会有同步等待。我们真正要区分的是，这段等待只是合理的跨硬件换手，还是已经拖跨了帧预算。

### 正常 trace：先把三段时间线连起来

先从 App / RenderThread 侧找到 `queueBuffer()` 或 `eglSwapBuffers()`，再去 SurfaceFlinger 侧看 `latchBuffer`、composition、`presentDisplay()`，最后结合 GPU busy 片段和 BufferQueue 状态。只要这三段能对上，我们就能回答两个关键问题：第一，producer 是不是按时把新帧交出来了；第二，consumer 有没有在合理时间内把旧 buffer 释放回去。

[图：正常帧里的 Fence 流转。上半部分是 App/RenderThread 的 `queueBuffer()`，中间是 SurfaceFlinger 的 `latchBuffer` 与 composition，下半部分是 HWC `presentDisplay()` / present fence。标出 producer 写完成 fence、consumer release fence、present fence 三段时间关系。]

### 异常一：SurfaceFlinger 长时间等 acquire fence，根因通常在 producer 侧

如果 `latchBuffer` 或 client composition 前面有长时间 wait，而同一时段 GPU 也很忙，通常说明 producer 交出来的 buffer 还没真正写完。此时瓶颈更像是 RenderThread / GPU 渲染慢，而不是 SurfaceFlinger 自己慢。SurfaceFlinger 只是在等一条“读之前先等我写完”的 acquire fence。

[图：异常案例一，SurfaceFlinger `latchBuffer` 长时间等待 acquire fence。标出等待区间、对应 GPU busy slice，以及同一窗口的 BufferQueue 状态。]

### 异常二：App 长时间等 release fence，根因通常在 consumer 侧占着旧 buffer 不放

如果 App 侧 `dequeueBuffer()` 明显变长，同时同一窗口的旧 buffer 很久没有回收，问题更可能出在 consumer 侧。要么 SurfaceFlinger / HWC 合成慢，要么 display 侧迟迟没有把旧 buffer 替换掉。这里 producer 等的不是“我自己写完没有”，而是“对方到底什么时候读完”。

[图：异常案例二，BufferQueue 长时间满载。标出 App 侧 `dequeueBuffer()` 阻塞、SurfaceFlinger 侧 release fence 延迟，以及同一窗口多帧 `queued/acquired` 累积。]

### 不要背死阈值，要在同一条 trace 里做关联

“60fps 时 `queued` 在 0-1 之间正常，持续到 2 就异常”这种口诀太容易误导。不同刷新率、BLAST 与非 BLAST、SurfaceView 与 TextureView、可用 slot 数量和厂商实现都可能改变这个形态。更可靠的做法是只在同一条 trace、同一个窗口类型、同一台设备上做关联判断：如果某个窗口连续多帧处于高占用状态，同时 App 侧 `dequeueBuffer()` 变长，或者 SurfaceFlinger `latchBuffer` wait 与 GPU busy 对齐，我们再把它当成 congestion signal。否则，单看一个数字没有太大意义。

## 版本演进：真正变化的不是“有没有 Fence”，而是谁负责什么

### Android 7：HWC2 已经把 acquire / release / present fence 语义钉清楚

这一版最重要的变化，不是“第一次有 fence”，而是 HWC2 接口把每层 buffer 输入、release fence 回收、present fence 返回的职责分得更清楚。对排查来说，这意味着我们可以明确问：当前等待发生在 producer 交帧之前，还是 consumer 释放旧帧之后，而不是把所有等待都糊成一个“显示慢”。

### Android 8+：userspace 已经能看到 modern `sync_file` API，legacy 名词继续保留

`system/core/libsync/sync.c` 在 Android 8.1 就同时有 legacy 和 modern 两套查询 / merge 路径，所以“Android 10 才迁移到 libsync”也不准确。更贴近源码的说法是：Android 8+ 的 userspace 已经能看到 `sync_file_info`、`sync_fence_info` 这类 modern API，后续版本继续保留 legacy `sync_timeline` / `sync_pt` 命名的兼容层与历史文档语境。

这也是我们今天读代码时经常会遇到的现象，文档还在讲 `sync_timeline`，调试工具却在打印 `sync_file_info`。不是一个新框架替换了另一个旧框架，而是同一套显式同步体系在不同层暴露出的命名不同。

### Android 14-16：变化重点在后端调度、FrameTimeline / ARR 配合，以及 release fence 路径

Skia 并不是 Android 14-16 才突然出现。`frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp` 在 `android-8.1.0_r81` 就已经存在，所以不能把这段历史写成“Android 14-16 全面切到 Skia”。更贴近事实的说法是，Skia 管线早就存在，后续版本的变化更多在后端调度、FrameTimeline、ARR 配合，以及 fence 的生成和观测路径上。

`android-16.0.0_r1` 的 `SkiaOpenGLPipeline.cpp` 里，GL 路径使用的是：

```cpp
skgpu::ganesh::FlushAndSubmit(surface);
mEglManager.createReleaseFence(true, &sync, &fence);
```

旧稿把这里写成另一条 flush-and-signal 路径，这会把读者带到错误的源码位置。更贴近实际源码的写法是：“当前 Android 16 的 GL backend 通过 `FlushAndSubmit(surface)` 提交，再由 `EglManager::createReleaseFence()` 生成 release fence。” 这样读者才能在 AOSP 里直接对上号。

[已验证: AOSP android-8.1.0_r81 / android-16.0.0_r1, frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp]

## 常见问题与误区

### `sw_sync` 不是普通 App 随便 signal 生产 fence 的后门

看到 `sw_sync_timeline_inc()` 公开存在，有人会顺手得出“那 fence 本来就是用户空间 signal 的”。这就把测试接口和生产路径混在一起了。`sw_sync` 解决的是测试、fallback 或特定软件管线的问题，它证明“用户空间绝对不能创建 software fence”这句话不成立，但不意味着常规图形栈里的 GPU / HWC fence 交由业务进程推进。

### fd 泄漏和 buffer 长时间回不来，不是一回事

拿到 fence fd 后忘记 close，确实会让进程 fd 数量持续上涨，这类问题适合先看 `/proc/<pid>/fd`。但“buffer 很久回不到 free pool”往往是另一类问题，它可能是 release fence 长时间不 signal，也可能是 consumer 生命周期没有结束，或者 BufferQueue 本身还持有 slot。前者该从进程 fd 和 fence 引用查起，后者该看 `dumpsys SurfaceFlinger`、BufferQueue 状态和对应窗口的 trace。把两类问题混成一句“fd 没关导致 buffer 永远不 free”，会把排查带偏。

### Fence wait 是症状，不一定是根因

看到长时间 `fence wait`，我们第一反应应该是“谁没按时完成自己的工作”。producer 侧渲染慢、consumer 侧合成慢、display 侧替换慢、GPU hang，都会把等待投影成 fence wait。Fence 把因果链暴露出来了，但它自己往往只是结果，不是根因。真正的根因还要结合 RenderThread、GPU、SurfaceFlinger 和 HWC 的上下文一起看。

## 与其他机制的关系

VSync 决定“一帧什么时候开始”，Fence 决定“这一帧在 producer 和 consumer 之间什么时候可以安全换手”。Choreographer 在 VSync-app 到来时组织 MainThread / RenderThread 启动一帧，RenderThread 在 `queueBuffer()` 时把“我可能还没写完”的 fence 一起交出去，这个 fd 到了 SurfaceFlinger / HWC 一侧就叫 acquire fence。反过来，SurfaceFlinger / HWC 释放旧 buffer 后返回的 fence，会在 producer 下一次 `dequeueBuffer()` 时表现为 release fence。BufferQueue 是这两条方向相反的 fence 的邮局，DMA-BUF / Gralloc 则负责让同一个 GraphicBuffer 能在不同进程和硬件单元之间被共享。

如果把这几章连起来看，逻辑会非常顺：VSync 管启动时机，MainThread / RenderThread 负责生产，BufferQueue 负责交接，Fence 负责同步，SurfaceFlinger / HWC 负责消费，present fence 则告诉我们“这帧到底什么时候真的显示出来了”。

## 参考资料

- AOSP 源码：`frameworks/native/libs/ui/Fence.cpp`
- AOSP 源码：`frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.h`
- AOSP 源码：`system/core/libsync/sw_sync.h`、`system/core/libsync/sync.c`
- AOSP 源码：`frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp`
- 官方文档：<https://source.android.com/docs/core/graphics/sync>
- 官方文档：<https://source.android.com/docs/core/graphics/architecture>
