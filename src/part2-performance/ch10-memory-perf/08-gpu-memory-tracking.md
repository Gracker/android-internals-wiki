---
title: "GPU / 图形内存统计与实战监控"
chapter: "10.8"
status: ready-for-review
applicable_versions: "Android 12 (API 31) - Android 17 (API 37)"
last_verified: "2026-06-07"
last_verified_against: "AOSP android-16.0.0_r1 / android-17.0.0_r1, perfetto.dev, developer.android.com"
confidence: medium
drafted_date: "2026-06-07"
drafted_by: "openclaw-task2a"
sources:
  - type: aosp
    path: "hardware/interfaces/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl"
  - type: aosp
    path: "frameworks/native/services/surfaceflinger/CompositionEngine/src/Output.cpp"
  - type: aosp
    path: "system/memory/libdmabufheap/BufferAllocator.cpp"
  - type: official
    path: "perfetto.dev/docs/data-sources/gpu"
  - type: official
    path: "developer.android.com/reference/android/graphics/Bitmap"
tags: [gpu-memory, dmabuf, gralloc, perfetto, memory-tracking, graphics, memtrack]
related_chapters: ["2.15", "4.2", "10.1", "14.8", "22.17", "23.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-06-07"
gap_source: "AOSP结构/章节深挖/官方文档"
---

# 10.8 GPU / 图形内存统计与实战监控

GPU 内存在 `dumpsys meminfo` 里常被一行 "Graphics" 带过，但它背后的分配路径、统计口径和监控手段，和 Java Heap 或 Native Heap 完全不同。图形 buffer 走 DMA-BUF / Gralloc 分配，计入 PSS 的方式依赖 `memtrack` HAL，而 HAL 实现又因 SoC 厂商而异。这节讲清楚 GPU 内存在 Android 上怎么被分配、怎么被统计、怎么被监控，以及 GPU 内存泄漏时用什么方法定位。

机制层面的图形内存分配流程（DMA-BUF Heaps、Gralloc 描述符、BufferQueue slot 管理）详见 2.15 节。本节聚焦**观测与归因**：拿到一份 `dumpsys meminfo` 或 Perfetto trace，如何判断 GPU 内存是否正常、哪里在增长、如何定位。

## 要点

### 🔹 锚点 1：GPU 内存在 Android 上的分配路径

Android 图形内存分两类：**共享内存**（DMA-BUF，跨进程可见，BufferQueue 传递的 buffer 属于此类）和 **GPU 私有内存**（GPU 内部纹理、着色器、命令缓冲区，对 CPU 侧不可见）。

共享内存的分配路径：应用通过 HWUI / Skia 构造 `GraphicBuffer`，Gralloc allocator 根据宽高、格式、usage 决定从哪个 DMA-BUF heap 分配。分配结果是一个 fd，通过 `GraphicBuffer::flatten()` 经 Binder 传递给 SurfaceFlinger 或其他消费者。这条路径在 2.15 节有完整展开。

GPU 私有内存由 GPU 驱动自行管理，AOSP 没有 HAL 层面的统一分配接口。Qualcomm Adreno、ARM Mali、Imagination 各有自己的显存管理策略，不经过 Gralloc。这部分内存的可见性依赖厂商的 debug 接口和 `memtrack` HAL 实现。

两者的统计口径不同：DMA-BUF 共享内存会出现在 `/proc/<pid>/smaps` 的 PSS 中（按共享比例分摊），而 GPU 私有内存只在 `memtrack` HAL 暴露时才被 `dumpsys meminfo` 的 "Graphics" 行捕获。[已验证: AOSP android-16.0.0_r1, hardware/interfaces/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl]

### 🔹 锚点 2：dumpsys meminfo 中 GPU / Graphics 内存解读

`adb shell dumpsys meminfo <pkg>` 的输出中，和 GPU 内存相关的行有：

- **Graphics**：`memtrack` HAL 报告的图形内存。包括 GPU 纹理、framebuffer、EGL surface 等被 HAL 追踪到的部分。
- **GL**：OpenGL ES / Vulkan 资源占用的内存。同样是 `memtrack` HAL 的上报范围。
- **Other Dev**：其他设备内存映射。某些 SoC 会把 GPU 相关的 mmap 区域记到这里。

[已验证: AOSP android-16.0.0_r1, hardware/interfaces/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl] Android 12 起的 AIDL `IMemtrack` 接口提供 `getMemory(int pid, MemtrackType type)` 方法，type 可以是 `GL` 或 `GRAPHICS`。HAL 返回的 `MemtrackRecord` 包含 size 和 flags。`FLAG_SMAPS_UNACCOUNTED` 表示这块内存不在 `/proc/<pid>/smaps` 的 PSS 里——此时 "Graphics" 行的数字包含了 `smaps` 无法感知的 GPU 私有部分。

不同设备上 "Graphics" 行的数字差异很大。Pixel 设备上 `memtrack` HAL 实现比较完整，Graphics 数字能覆盖大部分 GPU 纹理和 framebuffer；部分 OEM 设备上 HAL 只上报一部分，Graphics 行可能明显偏低。分析 GPU 内存问题时，先确认设备的 `memtrack` 覆盖范围——在同一台设备上做前后对比才有意义，跨设备比绝对值不靠谱。

`adb shell dumpsys gpu` 可以看系统级 GPU 内存概览。输出格式因 OEM 而异，但通常会包含全局 GPU 内存使用量和按进程的 GPU 分配。这条命令在排查 "谁吃了 GPU 内存" 时比 `dumpsys meminfo` 更直接，但稳定性不如 `meminfo`。

`adb shell dumpsys gfxinfo <pkg>` 的输出聚焦帧率和渲染管线状态，不直接报告 GPU 内存大小。但 `gfxinfo` 中的帧数据和 GPU 内存消耗有关联：大量纹理加载时帧耗时上升、GPU 利用率升高，可以和 `meminfo` 趋势交叉验证。

### 🔹 锚点 3：Perfetto GPU Memory 计数器与 SQL 查询

Perfetto 提供三个 GPU 相关数据源用于内存分析：

**`gpu.counters`**：采集 GPU 硬件计数器，包括频率、利用率、带宽。不直接报告内存大小，但可以观察 GPU 利用率和带宽趋势，辅助判断 GPU 负载和内存压力的相关性。采集配置需要指定可用的 counter 列表，不同 GPU 支持的 counter 不同。

**`gpu.renderstages`**：记录 GPU 执行各渲染阶段的时间。可以和 CPU 侧的 `doFrame` / `drawFrames` 对齐，看 GPU 端实际执行耗时。和内存分析的关联在于：如果 GPU render stage 中 texture upload 阶段持续偏长，说明有大量新纹理在加载，对应的 GPU 内存也在增长。[已验证: perfetto.dev/docs/data-sources/gpu]

**`gpu.track` / `gpu.memory`**：Perfetto UI 中的 GPU memory 轨道。Android 14+ 部分设备支持 `android.gpu.memory` 数据源，可以在 Perfetto 中看到进程级别的 GPU 内存变化曲线。这项功能的可用性取决于 GPU 厂商的 Perfetto producer 实现——Adreno 设备支持较好，Mali 设备需要确认具体型号。

Perfetto SQL 查询 GPU 内存（在支持 `gpu.memory` 数据源的设备上）：

```sql
-- 按进程聚合 GPU 内存快照
SELECT
  t.ts,
  t.value / 1024.0 AS gpu_mem_kb,
  p.name AS process_name
FROM counter c
JOIN track t ON c.track_id = t.id
JOIN process_track pt ON pt.id = t.id
JOIN process p USING (upid)
WHERE t.name GLOB '*gpu*memory*'
ORDER BY t.ts DESC
LIMIT 50;
```

上面这个查询在不同设备上需要根据实际的 track name 做调整。先用 `SELECT name FROM track WHERE name GLOB '*gpu*'` 查看设备上有哪些 GPU 相关 track。

如果设备不支持 `gpu.memory` 数据源，退回到 `dumpsys meminfo` 的定时采集方案：每 5 秒抓一次 Graphics 行，用脚本记录趋势。

### 🔹 锚点 4：procfs / sysfs 中的 GPU 内存指标

系统级 GPU 内存信息可以从 debugfs / procfs 获取，但多数路径需要 root 权限。

**DMA-BUF 统计**：

```bash
# 列出所有 dma-buf 及其大小和导出者
adb shell su -c "cat /sys/kernel/debug/dma_buf/bufinfo"
# 按进程统计 dma-buf 占用
adb shell su -c "cat /proc/<pid>/dmabuf"
```

`/sys/kernel/debug/dma_buf/bufinfo` 列出每个 DMA-BUF 的大小、导出者（expander）和当前 attach 的设备。这个信息可以确认哪些进程持有大量图形 buffer。Android 12+ 部分设备上 `/proc/<pid>/dmabuf` 也提供进程级 DMA-BUF 统计。[待验证: `/proc/<pid>/dmabuf` 在 Android 16/17 userdebug 版本上的可用性——部分内核配置可能未启用]

**GPU 厂商专用路径**：

| GPU | 路径 | 内容 |
|-----|------|------|
| ARM Mali | `/sys/kernel/debug/mali/gpu_memory`（或 `/d/mali/gpu_memory`） | 全局 GPU 内存使用量 |
| Qualcomm Adreno | `/sys/class/kgsl/kgsl-3d0/gpu_mm_heap` 或 `kgsl_proc/<pid>/` | 进程级 GPU 内存统计 |
| Imagination | `/sys/kernel/debug/pvr/` | PowerVR debug 信息 |

这些路径在 userdebug / eng 版本可用，user 版本通常被 SELinux 隐藏。`adb shell su -c "ls /sys/kernel/debug/"` 先确认设备上有哪些 debug 目录。

`/proc/<pid>/smaps` 中也可以间接看到 GPU 相关映射：搜索 `dmabuf`、`gpu`、`mali`、`kgsl` 等关键字，对应的 VMA 区域大小加起来就是进程通过 mmap 访问的 GPU buffer 大小。但这只包含 CPU 侧 mmap 的部分，GPU 私有纹理不算在内。

### 🔹 锚点 5：GPU 内存泄漏的诊断方法

GPU 内存泄漏的常见模式：

**Hardware Bitmap 未回收**：`Bitmap.Config.HARDWARE` 的像素存在 GPU / graphics 内存中，Java 侧只有轻量引用。如果 Bitmap 对象生命周期管理不当（比如缓存池只清了引用没等 GPU 侧释放），Graphics 行会持续增长。诊断方法：反复进出含大图的页面，每次返回后抓 `dumpsys meminfo`，如果 Graphics 不回落，检查 Bitmap 缓存策略。详见 22.17 节对 Hardware Bitmap 资源代价的分析。

**Surface / EGL Context 泄漏**：SurfaceView、TextureView、MediaCodec 的 Surface 如果没有正确释放，对应的 GraphicBuffer 和 EGL surface 会一直占 GPU 内存。`dumpsys meminfo` 里 Graphics 和 GL 行同时增长时，优先排查 Surface 生命周期。

**RenderScript / Vulkan 资源泄漏**：Allocation、VkImage、VkDeviceMemory 如果没有在正确的生命周期释放，GPU 内存不会回收。这类泄漏在 `dumpsys meminfo` 的 Other Dev 行可能有体现，但更常见的是只有通过 GPU 厂商的 debug 接口才能看到。

**诊断流程**：

1. 建立基线：冷启动后抓 `dumpsys meminfo`，记录 Graphics / GL 行的基线值
2. 操作复现路径：反复执行疑似泄漏的操作（如列表滑动、图片加载、相机预览切换）
3. 每轮操作后抓 `dumpsys meminfo`，记录 Graphics 变化趋势
4. 如果 Graphics 持续增长且不回落，用 `adb shell dumpsys gpu` 看全局 GPU 内存是否同步增长
5. 如果有 root 设备，用 `/sys/kernel/debug/dma_buf/` 确认是否有大量未释放的 DMA-BUF

Heapprofd 可以追踪 Native 层分配来源，但图形 buffer 走 DMA-BUF / Gralloc 路径，不在 malloc 管辖范围内。要追踪 Gralloc 分配来源，需要 GPU 厂商的专用工具（如 Adreno Profiler、Mali GPU Debugger），或者用 Perfetto 的 `gpu.renderstages` 结合 CPU 侧调用栈做间接关联。

### 🔹 锚点 6：Android 17 图形内存管理变更

**16KB Page Size 对 GPU 内存的影响**：Android 16 起引入 16KB page size 支持，Android 17 继续推进。GPU 内存分配以 page 为最小单位，page size 从 4KB 增大到 16KB 意味着小 buffer 的内部碎片率增加。一张 1920×1080 ARGB_8888 的 buffer 约 8MB，不受影响；但大量小纹理或临时 buffer 的实际内存占用可能比 4KB page 模式高出 10-20%。2.24 节对 16KB page size 下的图形内存边界有详细分析。[已验证: 官方文档, developer.android.com/guide/practices/page-sizes]

**DMA-BUF Heaps 成熟度**：Android 12 引入 DMA-BUF Heaps 替代 ION，到 Android 17 已经是主要分配路径。GKI 2.0 内核中 `/dev/dma_heap/system` 和 `/dev/dma_heap/system_uncached` 是通用节点，厂商私有 heap 通过 sepolicy 控制访问。`libdmabufheap` 提供用户态封装，内部有 ION 回退逻辑。GPU 内存的分配请求最终由 Gralloc allocator 映射到具体的 heap。[已验证: AOSP android-17.0.0_r1, system/memory/libdmabufheap/BufferAllocator.cpp]

**Gralloc 4.0+ 对 GPU 内存追踪的改善**：Gralloc 4.0 (Android 11+) 和后续版本的 AIDL allocator 接口统一了描述符格式，让图形 buffer 的 usage、格式、尺寸信息在 framework 层可追踪。但 Gralloc 不直接报告已分配 buffer 的总量——这个数字仍然依赖 `memtrack` HAL 和 DMA-BUF debugfs。

**GPU 内存与 LMK 的交互**：GPU 占用的 DMA-BUF 会计入进程的 RSS/PSS，在高内存压力下 `lmkd` 会根据 `oom_score_adj` 选择 victim 进程。如果一个后台进程持有大量未释放的 GraphicBuffer（比如后台视频播放器、相机服务），它可能成为 LMK 的优先目标。4.4 节对 LMK 的选进程策略有展开。

### 🔹 锚点 7：GPU 内存优化实战建议

**Hardware Bitmap 的使用与回收时机**：对"只上屏不读写"的大图使用 `Bitmap.Config.HARDWARE`，减少 Java heap 压力和 texture upload 抖动。但 Hardware Bitmap 的 GPU 内存不参与 Java GC——必须在确定不再绘制时主动回收（recycle 或等引用链断开）。列表场景中建议限制 Hardware Bitmap 池大小，避免快速滑动时大量图片同时驻留 GPU 内存。详见 22.17 节。

**SurfaceView vs. TextureView 的 GPU 内存开销**：SurfaceView 有独立 BufferQueue，不占用应用 Surface 的合成资源；TextureView 的 buffer 需要被应用 Surface 的 RenderThread 绘制，多一次 GPU 采样和合成。同等场景下 TextureView 的 GPU 内存开销更高。如果不需要 View 层级的动画变换（旋转、缩放），优先用 SurfaceView。

**帧缓冲区数量与 GPU 内存的关系**：BufferQueue 的 maxBufferCount 默认是 3（三缓冲），每增加一个 buffer 就是多一张完整分辨率的 GraphicBuffer。4K 显示设备上一张 buffer 约 32MB，三缓冲就是约 96MB GPU 内存。大部分应用不需要手动调整 buffer 数量，但如果通过 `Surface.setDequeueBufferTimeout` 或自定义 BufferQueue 管理器改了 buffer count，需要评估 GPU 内存代价。

**大分辨率图片加载的 GPU 内存控制**：在 4K / 大屏设备上，全分辨率加载一张图片的 GPU 纹理可能达到数十 MB。图片库（Glide / Coil）的 `override(size)` / `target()` 可以控制解码尺寸，避免把 4K 原图直接上传到 GPU。`Bitmap.prepareToDraw()` 可以提前触发 texture upload，把首帧的 GPU 同步开销分摊到预加载阶段。

## 扩展

### 🔸 扩展点 1：不同 SoC 平台的 GPU 内存统计差异

`memtrack` HAL 的实现质量直接决定 `dumpsys meminfo` 中 Graphics / GL 行的准确性和完整性。

- **Qualcomm Adreno**：`memtrack` 实现覆盖较全，`dumpsys gpu` 输出包含进程级 GPU 内存明细。Adreno Profiler 可以追踪纹理和 buffer 的分配来源。
- **ARM Mali**：Mali 设备的 `memtrack` 实现因 OEM 而异。部分设备只报告 GL 内存不报告 Graphics，导致 `dumpsys meminfo` 中 Graphics 行偏低。Mali GPU Debugger 提供独立的内存追踪能力。
- **Samsung Xclipse (AMD RDNA)**：Samsung 定制的 GPU，debug 接口和 `memtrack` 行为与标准 Mali 不同，需要 Samsung 专用工具链。

OEM 自定义的 GPU 内存 debug 接口通常在 `/sys/kernel/debug/<vendor>/gpu/` 下，需要查阅对应 SoC 的厂商文档。[待验证: 各 SoC 平台在 Android 17 上的 `memtrack` 实现差异需要逐设备确认]

### 🔸 扩展点 2：GPU 内存与整体系统内存预算

在 4GB 以下内存的设备上，GPU 内存占用可能占系统总内存的 15-25%。如果前台应用同时持有大量 GPU 纹理和 Java heap 对象，后台进程的可用内存会快速收窄，触发 LMK。

GPU 纹理、framebuffer、DMA-BUF 的 PSS 计入方式是按共享比例分摊。一张被 2 个进程共享的 DMA-BUF，每个进程的 PSS 只记一半。但 SurfaceFlinger 持有的合成 buffer 通常被多个 layer 共享，PSSI 分摊后的数字可能低估了实际的 GPU 内存压力。

在低内存设备上做性能优化，除了关注 Java heap 和 Native heap，也要定期检查 Graphics 行的增长趋势。如果发现应用的 GPU 内存占用稳定在 100MB 以上，考虑减少同时可见的纹理数量、降低图片分辨率或使用 SurfaceView 替代 TextureView。

### 🔸 扩展点 3：Game / AR / Camera 场景的 GPU 内存管理

**游戏**：游戏是 GPU 内存消耗最高的应用类型。纹理、渲染目标（render target）、深度缓冲、命令缓冲都需要 GPU 内存。Unity / Unreal 引擎有自己的纹理流式加载（texture streaming）机制，根据相机距离动态调整纹理分辨率。`MemoryAdvice API`（详见 23.10 节）可以在系统内存压力升高时通知游戏释放资源。

**AR（ARCore）**：ARCore 的 GPU 内存消耗来自相机帧 buffer、点云数据渲染、平面检测的可视化层。多 AR session 切换时如果没有正确释放前一个 session 的资源，GPU 内存会累积。

**Camera**：Camera2 / CameraX 的 ImageReader 配置直接影响 GPU 内存：每一路输出 surface 都有独立的 BufferQueue，buffer 数量和分辨率决定了 GPU 内存占用。高分辨率 + 多路输出场景（如同时预览 + 录制 + 人脸检测）需要仔细计算 buffer 总量。

## DeepResearch 延伸参考

### Android 17 GPU 内存管理优化与显存池碎片整理技术
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-11-android17-gpu-memory-tracking-pool-defrag.md
- 类型：DeepResearch 调研结果
- 摘要：Android 17 AOSP 用户态不做显存分配和碎片整理，实际分配交给 gralloc/HAL 驱动层。AOSP 核心职责是观测：GpuMem 通过 eBPF 追踪 gpu_mem_total tracepoint，GpuMemTracer 推 Perfetto 数据源，GpuStats 通过 statsd pull atom 提供驱动统计。碎片整理是 gralloc 驱动内部职责，AOSP 只观测结果。
- 注入时间：2026-07-12
- 价值：纠正了「应用层池化+碎片整理」的常见误解，明确 AOSP GPU 内存管理的观测边界与 gralloc 职责分界
