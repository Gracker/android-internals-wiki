---

title: "Sync Fence 框架与帧同步机制"
chapter: "2.16"
section: "2.16"
applicable_versions: "Android 7 (API 24) - Android 17 (API 37)"
last_verified: "2026-04-26"
last_verified_against: "AOSP android-16.0.0_r1 / android-8.1.0_r81 / android-7.0.0_r1, SkiaOpenGLPipeline.cpp / SkiaVulkanPipeline.cpp / renderthread/VulkanManager.cpp, source.android.com/docs/core/graphics/sync"
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
  - type: aosp
    path: "frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/VulkanManager.cpp"
  - type: official
    path: "https://source.android.com/docs/core/graphics/sync"
  - type: official
    path: "https://source.android.com/docs/core/graphics/architecture"
tags: [sync-fence, fence, hwui, rendering, synchronization, timeline]
related_chapters: ["2.4", "2.5", "2.6", "2.13", "2.15"]
task2b_state: fixed
task9_result: pass-tech-review
task2b_result: fixed
task9_reviewed_date: "2026-05-24"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-24T15:30:04+08:00"
last_task2b_at: "2026-05-05T23:51:15+08:00"
repaired_date: "2026-04-26"
repaired_by: "openclaw-task2b"
task9_review_notes: "2026-05-05 task9 deep-review: needs-rework。2.16 P0 1；12.1 P1 1；P2 3 随队列记录。 | 2026-05-24 Task9 闲时抽检：needs-rework。P1 1：Vulkan Timeline Semaphore 不能直接导出 Android sync fd / Perfetto fence track 只能观察 native fence；P2 1：dequeueBuffer fence 命名需改为 dequeue/release fence。"
status: finalized
pipeline_stage: ready-to-publish
task6_state: "reviewed"
task6_result: pass-light-edit
task9_state: reviewed
reviewed_by: openclaw-task6
reviewed_date: "2026-05-06"
task6_reviewed_date: "2026-05-06"
last_task6_at: "2026-05-06T01:05:00+08:00"
last_task6_audit: "2026-06-15"
review_notes: "2026-04-27 task9 deep-review: pass-tech-review。无 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。P2 2 写入 suggestions。 | 2026-05-05 Task6 23:26：revisiting 写作复审，清理 fence 章节 L1/L2 表达（填充词、否定纠正式、参考资料重复块）；写作层通过。Task9 已有 P0 queue pending，等待 Task2B。 | 2026-05-06 Task6 01:05：Task2B 修复后写作复审，清理 L1/L2 表达与格式；无新增 L3/L4 回炉项，送 Task9 复审。 | 2026-05-06 Task9 01:28：复审通过。复核 HWC2 fence 语义、libsync merge、HWUI GL/Vulkan release fence、Timeline Semaphore 边界；无新增 P0/P1；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-05-24 Task9 deep-review: pass-tech-review。P0 0 / P1 0 / P2 1；Vulkan native fence 边界已改为 Binary Semaphore → sync fd 桥接，dequeue fence 命名已修正；仅留 Binary Semaphore reset 语义 P2 建议；queue 无 pending，Task6 已通过，自动晋升 finalized。"
last_task9_audit: "2026-06-14"
last_task9_review_log: "logs/deep-review/2026-05-24-15-deep-review.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-05-29
---

# 2.16 Sync Fence 框架与帧同步机制

当我们在 Perfetto 里看到 `latchBuffer`、`presentDisplay()` 或 `dequeueBuffer()` 旁边挂着一段 `fence wait` 时，重点在于追清楚这个 buffer 现在归谁用、什么时候才能安全换手。光记一个“这里卡了 X 毫秒”对排查没有帮助。Fence 就是这条换手协议。

App、GPU、SurfaceFlinger、HWC、Display Controller 都在异步工作。App 调完 `queueBuffer()`，不等于 GPU 已经把像素写完；`presentDisplay()` 返回了，也不等于屏幕已经完成这一帧扫描显示。如果没有显式同步，系统只能靠猜时机来复用 buffer，不是撕裂，就是白等。Fence 把“还没完成但迟早会完成”的状态封装成一个可传递、可等待、可调试的 fd，于是我们才能既避免读半成品，又把等待精确归因到 producer、consumer 或 display 侧。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **Fence 为什么存在**：[已验证: source.android.com/docs/core/graphics/sync]
  显式同步解决 CPU、GPU、HWC、Display Controller 异步读写同一 buffer 的先后次序问题，避免半成品被消费，也避免靠固定 sleep 猜时机。

- 🔹 **legacy Android sync framework 与 modern sync_file API 的关系**：[已验证: AOSP android-8.1.0_r81, system/core/libsync/sync.c]
  文档里常见 `sync_timeline`、`sync_pt`、`sync_fence`，当前 userspace 更常见 `sync_file_info`、`sync_fence_info` 等 modern API。前者是理解模型和兼容层名词，后者是现代调试接口。

- 🔹 **Acquire fence、Release fence、Present fence 的方向与两侧视角**：[已验证: source.android.com/docs/core/graphics/sync, AOSP android-7.0.0_r1 HWC2.h]
  producer 在 `queueBuffer()` 输入的 fence，到了 consumer 一侧就叫 acquire fence；consumer 在 `getReleaseFences()` / `releaseBuffer()` 返回的 fence，回到 producer 下一次 `dequeueBuffer()` 时就是“写之前先等我读完”的 release fence；present fence 表示本帧上屏。

- 🔹 **Fence Merge 解释多 layer 合成里的多对一等待**：[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/Fence.cpp, system/core/libsync/sync.c]
  `Fence::merge()` / `sync_merge()` 可以把多条 fence fd 合成一个等待对象。合并后的 fence 要等所有输入 fence signal 后才 signal，SurfaceFlinger client composition 和 HWC 多层提交都依赖这个语义。

- 🔹 **在 Perfetto 中如何判断 fence 是正常同步还是掉帧瓶颈**：[已验证: source.android.com/docs/core/graphics/architecture]
  需要把 `queueBuffer()`、`latchBuffer`、`presentDisplay()`、BufferQueue 状态和 GPU busy 片段连起来看，不能只盯一段 `fence wait`。

- 🔹 **版本演进的真实主线**：[已验证: AOSP android-7.0.0_r1 HWC2.h, android-8.1.0_r81 system/core/libsync/sync.c, android-16.0.0_r1 SkiaOpenGLPipeline.cpp / SkiaVulkanPipeline.cpp / renderthread/VulkanManager.cpp]
  Android 7 已有 HWC2；Android 8+ 用户空间已经能看到 modern libsync / sync_file API；Skia 管线在 Android 8.1 已存在。Android 14-16 核对 release fence 时要分 GL/EGL 与 Vulkan 两条后端：GL 看 `SkiaOpenGLPipeline.cpp` / `EglManager::createReleaseFence()`，Vulkan 看 `SkiaVulkanPipeline.cpp` / `VulkanManager::createReleaseFence()` / `presentFence`。

### 扩展（可选深入）

- 🔸 **sw_sync 的边界**：`sw_sync` 保留测试与特定软件管线接口；生产路径中的 acquire / release / present fence 仍由内核驱动或硬件推进。生产设备 user build 上，普通 App 通常无法访问 `/dev/sw_sync` 或 `/sys/kernel/debug/sync`。
- 🔸 **常见误区**：fd 泄漏、slot 长时间不可复用、GPU hang 是三类不同问题，排查入口不能混用。
<!-- outline-end -->

## 为什么需要 Fence：渲染管线不是一条直线

如果没有显式同步，producer 只能靠“我猜你差不多用完了”来复用 buffer。桌面系统有时还能把这种不确定性交给单一驱动兜底，Android 不行。这里至少有 App、BufferQueue、SurfaceFlinger、HWC、Display Controller 五个环节，跨线程、跨进程、跨硬件单元是常态，任何一段快一点或慢一点，都会影响同一个 GraphicBuffer 什么时候能读、什么时候能写。

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

把这三层拆开后，很多“资料和源码对不上”的困惑就消失了。旧文档在讲概念模型，libsync 在讲 userspace 查询接口，驱动代码则在讲内核对象本身，它们站在不同抽象层。

### Fence Merge：多条 fence 合成一个等待对象

单层 buffer 示例只覆盖一对一传递；多 layer 合成需要把多条 acquire fence 收束成一个等待对象。AOSP 的入口是 `frameworks/native/libs/ui/Fence.cpp` 里的 `Fence::merge()`，它向下调用 `system/core/libsync/sync.c` 的 `sync_merge()`。返回的新 fd 代表一组 fence 的合集，只有所有输入 fence 都 signal 后才会 signal。

这个语义支撑 Client Composition 和 HWC 多层提交。比如同一帧里既有 App 主 Surface，又有 SurfaceView 或视频 layer，SurfaceFlinger 不能只等其中一条 fence；它需要把多个 producer 的完成点合并成一个可传递对象，再交给后续合成或显示阶段。Perfetto 里看到一个 wait 覆盖多个 buffer 的完成状态时，可以沿 `Fence::merge()` / `sync_merge()` 去核对。

[已验证: AOSP android-16.0.0_r1, frameworks/native/libs/ui/Fence.cpp, system/core/libsync/sync.c]

### sw_sync 的边界：测试接口受权限和场景限制

`android-16.0.0_r1` 的 `system/core/libsync/sw_sync.h` 公开了下面三个接口：

```c
int sw_sync_timeline_create(void);
int sw_sync_timeline_inc(int fd, unsigned count);
int sw_sync_fence_create(int fd, const char *name, unsigned value);
```

这些接口说明 Android 保留了 userspace software timeline 能力。生产路径里的 GPU、HWC、display fence 仍由内核驱动或硬件 signal，以保证 forward progress；`sw_sync` 主要服务内核开发测试、模拟器、root/debug 环境和少量软件管线。

生产设备的 user build 上，普通 App 通常无法打开 `/dev/sw_sync`，也无法读取 `/sys/kernel/debug/sync` 这类 debugfs 节点。访问权限会被文件权限、SELinux domain、root/system/graphics 组策略共同限制。排查图形问题时，可以把 `sw_sync` 当作测试和调试入口，不能把它写成业务进程控制 acquire / release / present fence 的方案。

[已验证: AOSP android-16.0.0_r1, system/core/libsync/sw_sync.h]

## 渲染管线里的三类 Fence

先把方向钉住。Fence 的名字经常让人绕晕。**同一个 fd 从 producer 这边传到 consumer 那边，语义会跟着观察角度变化**。

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

这也是为什么我们不能把 producer 在 `queueBuffer()` 输入的那个 fence 写成 release fence。**producer `queueBuffer()` 输入的 fence，到 consumer 一侧叫 acquire fence；consumer 返回给 producer 的 fence，才是 release fence。** 两边说的是同一轮 buffer 交接的两个方向。

如果把这两个方向说反，后面分析 `dequeueBuffer()` 阻塞和 `latchBuffer` 等待时就一定会乱。一个常见误判是把 App 侧等待旧 buffer 可重用的时间，写成“等待 acquire fence”；它等的是 consumer 返回来的 release fence，只是 producer 拿到的字段名未必总把这个语义写在脸上。

### Present fence（旧资料里也常叫 retire fence）：本帧上屏的时刻

present fence 是每帧一个，它在 `presentDisplay()` 之后返回。对物理屏来说，它表示当前帧出现在屏幕上的时间点；对虚拟显示来说，它表示什么时候可以安全读取输出 buffer。HWC1 文档里常见 retire fence 这个名字，HWC2/HWC3 语境下更常用 present fence；读旧资料时要把协议版本和术语放在一起看。

这条 fence 很适合用来理解端到端显示延迟。`queueBuffer()` 只能说明 producer 把帧交出来了，present fence 才更接近“用户什么时候实际看到这一帧”。如果我们在 SurfaceFlinger / HWC 侧做帧耗时分析，不把 present fence 连起来看，很容易把“已经提交”和“已经显示”混为一谈。

[已验证: source.android.com/docs/core/graphics/sync]

## 在 Perfetto 里怎么读 Fence

Fence wait 本身不是 bug。正常渲染里本来就会有同步等待。要区分的是，这段等待只是合理的跨硬件换手，还是已经拖跨了帧预算。

### 正常 trace：先把三段时间线连起来

从 App / RenderThread 侧找到 `queueBuffer()` 或 `eglSwapBuffers()`，再去 SurfaceFlinger 侧看 `latchBuffer`、composition、`presentDisplay()`，并结合 GPU busy 片段和 BufferQueue 状态。只要这三段能对上，我们就能回答两个关键问题：第一，producer 是不是按时把新帧交出来了；第二，consumer 有没有在合理时间内把旧 buffer 释放回去。

[图：正常帧里的 Fence 流转。上半部分是 App/RenderThread 的 `queueBuffer()`，中间是 SurfaceFlinger 的 `latchBuffer` 与 composition，下半部分是 HWC `presentDisplay()` / present fence。标出 producer 写完成 fence、consumer release fence、present fence 三段时间关系。]

### 异常一：SurfaceFlinger 长时间等 acquire fence，根因通常在 producer 侧

如果 `latchBuffer` 或 client composition 前面有长时间 wait，而同一时段 GPU 也很忙，通常说明 producer 交出来的 buffer 还没有完成写入。此时瓶颈更像是 RenderThread / GPU 渲染慢，而不是 SurfaceFlinger 自己慢。SurfaceFlinger 只是在等一条“读之前先等我写完”的 acquire fence。

[图：异常案例一，SurfaceFlinger `latchBuffer` 长时间等待 acquire fence。标出等待区间、对应 GPU busy slice，以及同一窗口的 BufferQueue 状态。]

### 异常二：App 长时间等 release fence，根因通常在 consumer 侧占着旧 buffer 不放

如果 App 侧 `dequeueBuffer()` 明显变长，同时同一窗口的旧 buffer 很久没有回收，问题更可能出在 consumer 侧。要么 SurfaceFlinger / HWC 合成慢，要么 display 侧迟迟没有把旧 buffer 替换掉。这里 producer 等的是“对方到底什么时候读完”，不是“我自己写完没有”。

[图：异常案例二，BufferQueue 长时间满载。标出 App 侧 `dequeueBuffer()` 阻塞、SurfaceFlinger 侧 release fence 延迟，以及同一窗口多帧 `queued/acquired` 累积。]

### 不要背死阈值，要在同一条 trace 里做关联

“60fps 时 `queued` 在 0-1 之间正常，持续到 2 就异常”这种口诀太容易误导。不同刷新率、BLAST 与非 BLAST、SurfaceView 与 TextureView、可用 slot 数量和厂商实现都可能改变这个形态。只在同一条 trace、同一个窗口类型、同一台设备上做关联判断：如果某个窗口连续多帧处于高占用状态，同时 App 侧 `dequeueBuffer()` 变长，或者 SurfaceFlinger `latchBuffer` wait 和 GPU busy 时间重合，我们再把它当成 congestion signal。否则，单看一个数字没有太大意义。

## 版本演进：变化的是谁负责什么

### Android 7：HWC2 已经把 acquire / release / present fence 语义钉清楚

这一版最重要的变化，是 HWC2 接口把每层 buffer 输入、release fence 回收、present fence 返回的职责分得更清楚。对排查来说，这个拆分让我们可以明确问：当前等待发生在 producer 交帧之前，还是 consumer 释放旧帧之后。把所有等待都糊成一个“显示慢”，排查就失去了方向。

### Android 8+：userspace 已经能看到 modern `sync_file` API，legacy 名词继续保留

`system/core/libsync/sync.c` 在 Android 8.1 就同时有 legacy 和 modern 两套查询 / merge 路径，所以“Android 10 才迁移到 libsync”也不准确。Android 8+ 的 userspace 已经能看到 `sync_file_info`、`sync_fence_info` 这类 modern API，后续版本继续保留 legacy `sync_timeline` / `sync_pt` 命名的兼容层与历史文档语境。

这也是我们今天读代码时经常会遇到的现象，文档还在讲 `sync_timeline`，调试工具却在打印 `sync_file_info`。同一套显式同步体系在不同层暴露出的命名不同。

### Android 14-16：GL/EGL 与 Vulkan 的 release fence 路径要分开看

Skia 管线在 Android 8.1 源码里已经存在。Android 16 的 HWUI 后端不能写成 Graphite 已验证路径。AOSP android-16.0.0_r1 的 `frameworks/base/libs/hwui/pipeline/skia/` 目录包含 `SkiaOpenGLPipeline.cpp`、`SkiaVulkanPipeline.cpp`、`SkiaGpuPipeline.cpp`；没有 `SkiaGraphitePipeline.cpp`。如果后续讨论 Graphite，只能标成非该 tag 已验证路径或待核对内容。

GL 后端的 release fence 入口在 `SkiaOpenGLPipeline::flush()`。读代码时看下面两行就够：

```cpp
skgpu::ganesh::FlushAndSubmit(surface);
mEglManager.createReleaseFence(true, &sync, &fence);
```

这条路径先通过 Ganesh flush/submit 提交，再让 `EglManager::createReleaseFence()` 创建 native fence；如果设备不支持 native fence，代码会退到 EGL sync wait 后返回无效 fd。

Vulkan HWUI 后端走另一条入口。`SkiaVulkanPipeline::flush()` 直接调用 `VulkanManager`：

```cpp
vulkanManager().createReleaseFence(&fence, mRenderThread.getGrContext());
```

`VulkanManager::createReleaseFence()` 会创建可导出 sync fd 的 `VkSemaphore`，通过 Skia `GrFlushInfo` signal semaphore，再用 `vkGetSemaphoreFdKHR` 导出 fence fd。`finishFrame()` 还会返回 `presentFence`，并在 `VulkanManager::swapBuffers()` 里随当前 buffer 提交给底层 surface。

Trace 分析时，GL 后端把 `flush commands`、EGL release fence、SurfaceFlinger acquire/release fence 放在同一时间窗里看。Vulkan 后端还要把 GPU queue submit、semaphore 导出的 sync fd、`presentFence` 和 FrameTimeline 放在同一时间窗里看。这样才能判断等待来自 HWUI 后端提交、SurfaceFlinger 消费，还是显示侧 present。

[已验证: AOSP android-8.1.0_r81 / android-16.0.0_r1, frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp, frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp, frameworks/base/libs/hwui/renderthread/VulkanManager.cpp]

## Vulkan Timeline Semaphores：从一次性 fd 到长效计数器（Android 16）

前面的内容围绕 `dma_fence` / `sync_fence` 的 fd 模型展开——每个同步点对应一个 fd，signal 后就失效，多轮同步需要反复创建和传递新 fd。Vulkan Timeline Semaphores 是另一套同步模型，属于 Vulkan 1.2 核心特性。实际可用性取决于设备 GPU 驱动是否暴露 `VkPhysicalDeviceTimelineSemaphoreFeatures.timelineSemaphore`。

### Binary Semaphore vs Timeline Semaphore

传统 Vulkan Binary Semaphore 的行为和 `sync_fence` 的 fd 类似：signal 一次后回到 unsignal 状态，只能表达"这一轮完成了"。Timeline Semaphore 引入了 64 位单调计数器：每次 signal 时计数器递增，等待端可以指定"我等计数器到达某个值"。于是同一个 semaphore 对象可以跨多轮使用，不需要每轮创建新的 fd。

```cpp
// Timeline Semaphore 的等待语义
VkSemaphoreWaitInfo waitInfo{};
waitInfo.sType = VK_STRUCTURE_TYPE_SEMAPHORE_WAIT_INFO;
waitInfo.semaphoreCount = 1;
waitInfo.pSemaphores = &timelineSemaphore;
waitInfo.pValues = &waitValue;  // 等计数器到达这个值
vkWaitSemaphores(device, &waitInfo, UINT64_MAX);
```

### Binary Semaphore Export：HWUI 当前的真实路径

进入 Android 图形栈边界时，需要通过 fd export/import 衔接 Vulkan 与 native fence。当前 AOSP `android-16.0.0_r1` 中 HWUI 的实际路径使用的是 **Binary Semaphore**（非 Timeline Semaphore）：

1. `VulkanManager::createReleaseFence()` 创建一个带有 `VkExportSemaphoreCreateInfo(VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT)` 的 `VkSemaphore`——这是 Binary Semaphore
2. 通过 `GrFlushInfo` 把 semaphore 附加到 Skia flush 操作，GPU 完成后 signal
3. 调用 `vkGetSemaphoreFdKHR` 导出 sync fd
4. 这个 fd 随 buffer 通过 `queueBuffer()` 交给 BufferQueue → SurfaceFlinger
5. SurfaceFlinger/HWC 侧拿到的就是标准 native fence fd，走正常 acquire/release 流程

反向同理：`dequeueBuffer()` 返回的 fence fd（AOSP `VulkanManager.cpp` 字段名 `bufferInfo->dequeue_fence`）通过 `vkImportSemaphoreFdKHR` 导入为 Vulkan Binary Semaphore，GPU 等待该 semaphore 后再开始写入 buffer。这个 fd 按 Android 图形同步语义是 release fence（consumer 释放旧 buffer 给 producer），不是 BufferQueue acquire fence——两者方向不同，不要混淆。

注意：`VulkanManager::createReleaseFence()` / `finishFrame()` 并没有设置 `VkSemaphoreTypeCreateInfo`（Timeline Semaphore 需要 `semaphoreType = VK_SEMAPHORE_TYPE_TIMELINE`），所以当前 HWUI 导出的都是 Binary Semaphore，与 WSI / native fence 的语义完全匹配。

### Timeline Semaphore 与 Binary Semaphore 的分工

Timeline Semaphore 优化的是 Vulkan 队列内部的多帧同步——用一个 64 位计数器替代多轮 Binary Semaphore，减少同步对象分配开销并支持提前提交。但 WSI / native fence 边界仍然以 Binary Semaphore fd 为交换格式，原因是 `dma_fence` / `sync_file` 的内核语义就是一次性的 signal/wait。

所以"Vulkan 用了 Timeline Semaphore"和"Android 图形栈还在用 Binary Semaphore fd"不矛盾——Timeline Semaphore 优化的是 Vulkan 队列内部，Binary Semaphore export/import 负责 Vulkan 与 Android 图形栈的桥接。

### 对图形管线的影响

**Vulkan 内部减少同步对象开销。** 传统 Vulkan Binary Semaphore 每轮 submit 都需要独立的 semaphore/fence 对象。Timeline Semaphore 用一个 64 位计数器替代了多轮 binary semaphore，减少了 Vulkan 队列内部的同步对象分配和等待开销。

**支持 Vulkan 队列内提前提交。** 计数器模型允许 producer 提交第 N+1 帧的渲染命令，同时等待第 N 帧 fence signal（等待值 = N），而不是先等第 N 帧 signal 再提交第 N+1 帧。这种"提前提交等待"在流水线化的 GPU 命令提交中减少了上下文切换延迟。

**与 Android native fence fd 的边界。** Timeline Semaphore 是 Vulkan 同步模型内部的优化。Android 图形栈的跨进程/跨驱动边界——BufferQueue 的 `queueBuffer()` / `dequeueBuffer()`、SurfaceFlinger 的 `latchBuffer`、HWC 的 `setLayerBuffer` / `presentDisplay()`——仍然以 native fence / `sync_file` fd 作为交换格式。Vulkan 队列通过 `vkGetSemaphoreFdKHR`（`VK_KHR_external_semaphore_fd`）导出 sync fd 进入 Android 图形管线，或通过 `vkImportSemaphoreFdKHR` 导入外部 fence。HWUI 的 `SkiaVulkanPipeline` / `VulkanManager::createReleaseFence()` 正是走这条 export → import interop 路径。

**Perfetto 可观测性。** Perfetto 的 `android.fence` / fence wait slice 观测的是 native fence fd（`dma_fence`）的 signal/wait 事件，也就是 Vulkan 与 Android 图形栈边界上的 Binary Semaphore → sync fd 桥接。纯 Vulkan Timeline Semaphore 等待不会直接进入 `android.fence` 轨道，需要 GPU counter、Vulkan layer trace 或应用侧标记辅助观察。Vulkan 规范要求 `SYNC_FD` 这类 copy payload handle 导出使用 Binary Semaphore（`VUID-VkSemaphoreGetFdInfoKHR-handleType-03253`），所以 Android native fence 边界始终以 Binary Semaphore 为桥梁，不是 Timeline Semaphore 直接导出。

Timeline Semaphore 是 Vulkan 1.2 核心特性，实际可用性取决于设备 GPU 驱动是否支持 `VkPhysicalDeviceTimelineSemaphoreFeatures.timelineSemaphore`。Android 16 / VPA16 并未将 Timeline Semaphore 列为强制设备要求（VPA16 追加的是 `VK_EXT_host_image_copy`、maintenance6 等特性）。进入 Android native fence 边界的 interop 依赖 `VK_KHR_external_semaphore_fd` / `VK_KHR_external_fence_fd` 扩展。

### 16KB 页对 Fence 路径的潜在影响

[待验证：以下为研究假设，尚缺同机 4KB/16KB 内核对比的 kernel ftrace（irq/dma_fence signal、sched wakeup）与 Perfetto fence wait 尾部抖动的实测证据。]

16KB 页对 fence 同步路径的潜在影响不在 fence 对象本身，而在内核中断处理路径的 TLB 命中率。假设链条：GPU 完成渲染 → 通过中断通知 CPU → 内核中断处理函数访问 fence 状态所在内存页 → 16KB 页面扩大 TLB 覆盖范围 → 理论上减少中断路径 TLB Miss → 可能缩短 GPU signal 到 SurfaceFlinger wakeup 的延迟。

这条链条目前没有同机 4KB/16KB kernel ftrace（irq/dma_fence signal、sched wakeup）、perf counter（TLB miss）或 Perfetto fence wait 尾部抖动的实测对照。如果假设成立，高频 VSync（120Hz / 144Hz）设备受益更明显，因为帧间隔越短，fence signal 和下一帧 fence wait 之间的余量越小。验证方式：同设备分别启动 4KB/16KB 内核，对比 GPU IRQ 到 SurfaceFlinger wakeup 延迟、TLB miss perf counter，以及 Perfetto fence wait 尾部抖动。

### [待验证] 未来展望：Timeline Semaphore 与 fd 路径的演进

[待验证：以下为基于技术趋势的合理推测，当前未找到 Android 17 CDD、source.android.com 或 AOSP tag 中关于"强推 Timeline Semaphores"或"移除图形管线 fd 依赖"的公开依据。补到正式 API/CDD/AOSP 变更后再升级为确定内容。]

fd 泄漏是 Android 图形栈长期存在的稳定性隐患：一个未关闭的 fence fd 会阻止对应 buffer 被 Gralloc 回收，累积后可能触发图形栈卡死。Timeline Semaphore 的计数器模型理论上可以缓解 fd 泄漏问题，因为同一个 semaphore 对象在生命周期内被复用。但 Android 图形管线从 fd 模型迁移到 Timeline Semaphore 需要内核驱动、Gralloc、BufferQueue、SurfaceFlinger、HWC 的端到端配合，不是单方面可以推动的。

部分 Vulkan 设备可支持 timelineSemaphore（通过 VkPhysicalDeviceTimelineSemaphoreFeatures 查询）；Android 图形栈 native fence / sync_file fd 边界是否向 Timeline Semaphore 演进，以正式 CDD / AOSP / source.android.com 为准。对开发者来说，如果使用 Vulkan 直接渲染，现在就可以迁移到 Timeline Semaphores；如果通过 ANGLE 间接使用，迁移由系统层完成。

## 常见问题与误区

### `sw_sync` 不是普通 App 随便 signal 生产 fence 的后门

看到 `sw_sync_timeline_inc()` 公开存在，有人会顺手得出“那 fence 本来就是用户空间 signal 的”。这就把测试接口和生产路径混在一起了。`sw_sync` 解决的是测试、fallback 或特定软件管线的问题，它证明“用户空间绝对不能创建 software fence”这句话不成立，但不意味着常规图形栈里的 GPU / HWC fence 交由业务进程推进。

### fd 泄漏和 buffer 长时间回不来，不是一回事

拿到 fence fd 后忘记 close，会让进程 fd 数量持续上涨，这类问题适合先看 `/proc/<pid>/fd`。但“buffer 很久回不到 free pool”往往是另一类问题，它可能是 release fence 长时间不 signal，也可能是 consumer 生命周期没有结束，或者 BufferQueue 本身还持有 slot。前者该从进程 fd 和 fence 引用查起，后者该看 `dumpsys SurfaceFlinger`、BufferQueue 状态和对应窗口的 trace。把两类问题混成一句“fd 没关导致 buffer 永远不 free”，会把排查带偏。

### Fence wait 是症状，不一定是根因

看到长时间 `fence wait`，我们第一反应应该是“谁没按时完成自己的工作”。producer 侧渲染慢、consumer 侧合成慢、display 侧替换慢、GPU hang，都会把等待投影成 fence wait。Fence 把因果链暴露出来了，但它自己往往只是结果，不是根因。根因还要结合 RenderThread、GPU、SurfaceFlinger 和 HWC 的上下文一起看。

## 与其他机制的关系

VSync 决定“一帧什么时候开始”，Fence 决定“这一帧在 producer 和 consumer 之间什么时候可以安全换手”。Choreographer 在 VSync-app 到来时组织 MainThread / RenderThread 启动一帧，RenderThread 在 `queueBuffer()` 时把“我可能还没写完”的 fence 一起交出去，这个 fd 到了 SurfaceFlinger / HWC 一侧就叫 acquire fence。反过来，SurfaceFlinger / HWC 释放旧 buffer 后返回的 fence，会在 producer 下一次 `dequeueBuffer()` 时表现为 release fence。BufferQueue 是这两条方向相反的 fence 的邮局，DMA-BUF / Gralloc 则负责让同一个 GraphicBuffer 能在不同进程和硬件单元之间被共享。

如果把这几章连起来看，逻辑会非常顺：VSync 管启动时机，MainThread / RenderThread 负责生产，BufferQueue 负责交接，Fence 负责同步，SurfaceFlinger / HWC 负责消费，present fence 则告诉我们“这帧到底什么时候实际显示出来了”。

## 参考资料

### Android Sync Fence 机制深度剖析：从 dma-fence 到 Android 16 Explicit Sync
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Android Sync Fence 机制深度剖析-从 dma-fence 到 Android 16 Explicit Sync.md
- 类型：DeepResearch 调研结果
- 摘要：从 Linux 内核 dma_fence 结构体出发，详述 sync_file uABI、libsync 兼容桥到 Android libui Fence 类的完整流程。覆盖 fence 的 signal/wait/add_callback 语义、signalling critical section、dma_fence_chain merge/merge 架构、acquire/release/present fence 在 BufferQueue/SurfaceControl/HWC3 中的流转，以及 Android 16 explicit sync 与可观测性工具。
- 注入时间：2026-04-24（更新 2026-04-29）
- 价值：源码级贯通 Linux dma_fence 到 Android Sync Fence 的全流程，含 Android 16 Explicit Sync 迁移细节

- AOSP 源码：`frameworks/native/libs/ui/Fence.cpp`
- AOSP 源码：`frameworks/native/services/surfaceflinger/DisplayHardware/HWC2.h`
- AOSP 源码：`system/core/libsync/sw_sync.h`、`system/core/libsync/sync.c`
- AOSP 源码：`frameworks/base/libs/hwui/pipeline/skia/SkiaOpenGLPipeline.cpp`
- AOSP 源码：`frameworks/base/libs/hwui/pipeline/skia/SkiaVulkanPipeline.cpp`
- AOSP 源码：`frameworks/base/libs/hwui/renderthread/VulkanManager.cpp`
- 官方文档：<https://source.android.com/docs/core/graphics/sync>
- 官方文档：<https://source.android.com/docs/core/graphics/architecture>
