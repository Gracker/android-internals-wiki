---
title: "Camera HAL3 Buffer 管理与 BufferQueue 协作的内存模型"
chapter: "2.32"
section: "2.32"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
tags: [camera, hal3, buffer, bufferqueue, memory, performance]
related_chapters: ["2.13", "2.15", "2.16", "13.9", "18.14"]
last_verified: "2026-08-20"
last_verified_against: "android-17.0.0_r1 + android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: aosp
    path: "frameworks/av/services/camera/libcameraservice/device3/Camera3Device.cpp"
  - type: aosp
    path: "frameworks/av/services/camera/libcameraservice/device3/Camera3Stream.cpp"
  - type: aosp
    path: "frameworks/av/services/camera/libcameraservice/device3/Camera3OutputStream.cpp"
  - type: aosp
    path: "frameworks/av/services/camera/libcameraservice/device3/aidl/AidlCamera3OutputUtils.cpp"
  - type: aosp
    path: "hardware/interfaces/camera/device/aidl/android/hardware/camera/device/StreamBuffer.aidl"
  - type: aosp
    path: "hardware/interfaces/camera/device/aidl/android/hardware/camera/device/HalStream.aidl"
  - type: aosp
    path: "hardware/interfaces/camera/device/aidl/android/hardware/camera/device/ICameraDeviceCallback.aidl"
  - type: aosp
    path: "hardware/interfaces/camera/device/aidl/android/hardware/camera/device/ICameraDeviceSession.aidl"
  - type: aosp
    path: "hardware/interfaces/camera/metadata/aidl/android/hardware/camera/metadata/InfoSupportedBufferManagementVersion.aidl"
  - type: aosp
    path: "frameworks/native/libs/gui/BufferQueueProducer.cpp"
  - type: aosp
    path: "frameworks/native/libs/gui/BufferQueueConsumer.cpp"
  - type: aosp
    path: "kernel/common/drivers/dma-buf/dma-fence.c"
  - type: aosp
    path: "kernel/common/drivers/dma-buf/sync_file.c"
  - type: official
    path: "https://source.android.com/docs/core/camera/buffer-management-api"
  - type: official
    path: "https://source.android.com/docs/core/camera/camera3"
  - type: official
    path: "https://source.android.com/docs/core/architecture/16kb-page-size/16kb"
  - type: official
    path: "https://source.android.com/docs/whatsnew/android-17-release"
pipeline_stage: ready-to-publish
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
last_review_finalize_at: "2026-08-20"
last_review_finalize_run_id: "20260820-201032-20263da8"
---

# 2.32 Camera HAL3 Buffer 管理与 BufferQueue 协作的内存模型

Camera HAL3 并不维护一个供预览、录像、分析和拍照共用的 `GraphicBuffer`（图形缓冲区）池。Camera2 会配置若干输出 `Surface`，CameraService 为每路输出建立流（stream）；每条流再通过独立队列与 `Surface` 后面的消费方（consumer）协作。HAL 在这条链路中负责生产图像，而 `GraphicBuffer` 的分配、缓存、跨进程传递和回收，则由系统框架（framework）、图形内存分配器、BufferQueue、HAL 与消费方共同完成。

以下讨论以 Android 17（API 37）的 `android-17.0.0_r1` 标签和内核 `android17-6.18-2026-06_r6` 为源码边界。分析缓冲区所有权时，应先把握四条规则：

1. `HalStream.maxBuffers` 限制 HAL 同时持有、尚未归还的缓冲区数量，不是应用层的缓存配置；
2. `dequeueBuffer()` 返回的同步栅栏（fence）会成为 Camera HAL 写入前等待的 acquire fence；HAL 返回的 release fence，又会成为下游消费方读取该缓冲区前要等待的栅栏；
3. HAL buffer management（HAL 缓冲区管理）只把“提交捕获请求”和“取得输出缓冲区”两个动作分开，缓冲区仍来自相应的输出 `Surface`；
4. 预览正常并不代表录像或 `ImageReader` 正常，多输出场景必须逐条流检查。

## 1. 从请求—结果模型理解缓冲区

### 1.1 一个捕获请求可以有多个输出

应用创建 `CameraCaptureSession` 时，会把预览、录像、图像分析、JPEG、RAW 等 `Surface` 交给 Camera2。`Camera3Device::RequestThread` 随后把捕获设置、帧编号（frame number）和目标流送入 HAL。HAL 完成传感器采集、ISP（图像信号处理器）处理和后处理后，通过 `processCaptureResult()` 异步返回元数据与输出缓冲区。

下面的结构图用于区分控制流、像素流和各路消费方：

```text
Camera2 / CameraX
  └─ CameraCaptureSession
       └─ Camera3Device / RequestThread
            └─ Camera HAL3
                 ├─ preview stream  ─→ SurfaceView / SurfaceTexture
                 ├─ record stream   ─→ MediaCodec
                 ├─ analysis stream ─→ ImageReader
                 └─ still stream    ─→ JPEG / HEIC / RAW consumer
```

同一个帧编号对应的元数据和各路缓冲区可以分批返回。预览缓冲区已经进入 BufferQueue，只能说明预览输出有所进展；它不能证明分析缓冲区已被应用关闭，也不能证明视频编码器已经消费同一帧。

### 1.2 每条输出流都有自己的队列边界

`Camera3OutputStream` 持有目标 `Surface`，并以 `NATIVE_WINDOW_API_CAMERA` 连接生产方（producer）。`Surface` 后面的直接消费方决定缓冲区的用途：

| 输出目标 | 相机缓冲区的直接消费方 | 是否直接形成可见图层 |
|---|---|---|
| `SurfaceView` | SurfaceFlinger 一侧的 `Surface` 消费方 | 通常是独立子图层 |
| `TextureView` | 应用进程中的 `SurfaceTexture` | 否，宿主 HWUI 还要将其绘制到应用窗口 |
| `ImageReader` | `ImageReader` 或应用 | 否 |
| `MediaCodec` 输入 `Surface` | 视频编码器 | 否 |
| 自研 OpenGL 或 Vulkan 输入 | 应用的 GPU 渲染器 | 输入本身不直接上屏，渲染器还要生成第二路可见输出 |

因此，“HAL 是生产方、SurfaceFlinger 是消费方”只适用于部分预览拓扑。`TextureView`、`ImageReader`、视频编码器与自研渲染器各有不同的直接消费方。

## 2. `configureStreams()` 决定什么

CameraService 会把宽高、格式、色彩数据空间（dataspace）、旋转和消费方 usage（用途标志）等信息交给 HAL。Android 17 的 AIDL HAL 通过 `HalStream` 返回以下关键结果：

- `overrideFormat`：`IMPLEMENTATION_DEFINED` 输出可由 HAL 选择实际格式；
- `producerUsage`：输出流上 HAL 需要的 gralloc 用途标志；
- `consumerUsage`：输入流上 HAL 需要的用途标志；
- `maxBuffers`：HAL 同时可能持有的最大缓冲区数量；
- `overrideDataSpace`：允许覆盖的色彩数据空间；
- `enableHalBufferManager`：在会话级可配置（session-configurable）模式下，决定该流是否由 HAL 按需请求缓冲区。

系统框架会合并生产方与消费方的用途标志，再交给图形内存分配器。对于 `IMPLEMENTATION_DEFINED` 格式，最终布局可能取决于相机写入端以及显示、GPU、编解码器等读取端的组合要求，不能只根据公开像素格式推断步幅（stride）、平面偏移（plane offset）或压缩方式。

### 2.1 `maxBuffers` 与队列总量

Android 17 的 `Camera3OutputStream::configureConsumerQueueLocked()` 会先通过 `NATIVE_WINDOW_MIN_UNDEQUEUED_BUFFERS` 查询消费方要求保留、不能由生产方取走的最小缓冲区数（源码变量 `maxConsumerBuffers`），再计算基础队列容量：

```text
mTotalBufferCount =
    maxConsumerBuffers
    + camera_stream::max_buffers
```

这个值描述该输出 `Surface` 的基础队列容量；预览显示同步或 `PreviewFrameSpacer` 路径还可能在此基础上追加额外缓冲或 framework 缓存。消费方必须保留自己仍在读取或显示的缓冲区，HAL 也必须有空间推进处理流水线（pipeline）。`Camera3Stream::getBuffer()` 还会检查 HAL 已取走的缓冲区数量；达到 `max_buffers` 时，它会等待缓冲区返回，并把等待时间记录到 `wait on max_buffers` 延迟直方图中。

不能直接增大 `maxBuffers` 来掩盖消费方处理缓慢的问题。增加它可能让处理流水线暂时不阻塞，但也会增加该流中可同时驻留的图像内存。这个字段由 HAL 根据流水线需求声明，错误的数值还可能破坏系统框架与 HAL 的流量控制约定。

### 2.2 系统框架内部 BufferManager 与 HAL 缓冲区管理不同

源码中还有一个 `Camera3BufferManager`。它属于 CameraService 内部，可以让兼容的流复用系统框架管理的 `GraphicBuffer`，再通过 `attachBuffer()` 接入具体的 BufferQueue。启用后，`Camera3OutputStream` 会禁止相应的 BufferQueue 自行分配缓冲区。

HAL 缓冲区管理 API 则由 HAL 通过 `requestStreamBuffers()` 向 CameraService 取得缓冲区。两套机制可以出现在同一条调用路径中，但调用方、接口边界和目标都不同：

| 名称 | 所在侧 | 主要作用 |
|---|---|---|
| `Camera3BufferManager` | CameraService 内部 | 在系统框架管理的兼容流之间调度 `GraphicBuffer` |
| HAL 缓冲区管理 | Camera HAL 与 CameraService 之间 | 把捕获请求提交与输出缓冲区获取分开 |

排查日志或源码时，要先确认上下文所指的是哪一个 BufferManager。

## 3. 系统框架管理缓冲区时的一帧生命周期

某路输出未启用 HAL 缓冲区管理时，`RequestThread` 会在调用 HAL 前为该捕获请求取得输出缓冲区。

### 3.1 系统框架从 Surface 取得可写缓冲区

`Camera3OutputStream::getBufferLockedCommon()` 最终会调用 `ANativeWindow::dequeueBuffer()`。调用成功后得到：

- 一个 `ANativeWindowBuffer`，其句柄（handle）指向 `GraphicBuffer`；
- 一个栅栏文件描述符（fence fd），表示上一个消费方何时结束对该缓冲区的使用。

`Camera3OutputStream::getBufferLocked()` 把栅栏填入 `camera_stream_buffer.acquire_fence`，再把缓冲区交给 HAL。源码注释明确说明，此后这个 fence fd 由 HAL 持有。

### 3.2 HAL 等待 acquire fence 后写入图像

HAL 在读写缓冲区前必须等待 acquire fence。对于输出流，这一步能避免 HAL 覆盖 GPU、SurfaceFlinger、视频编码器或应用仍在读取的旧内容。

如果 acquire fence 为空，表示无需等待。若 HAL 因错误没有等待该栅栏，AIDL `StreamBuffer` 约定要求 HAL 把原 acquire fence 作为 release fence 退回，让系统框架在复用缓冲区前仍能等待正确的完成时刻。

### 3.3 HAL 用 release fence 归还写入结果

HAL 通过 `processCaptureResult()` 返回以下内容：

- 流与缓冲区标识；
- `BufferStatus.OK` 或 `ERROR`；
- release fence，表示 HAL 何时停止访问该缓冲区。

release fence 为空，表示调用 `processCaptureResult()` 时 HAL 已经完成所有访问。若栅栏有效，HAL 可以先返回结果，再由下游异步等待。栅栏发出信号（signal）后，HAL 不得再次访问该缓冲区。

### 3.4 CameraService 将缓冲区入队或取消

`Camera3OutputStream::returnBufferCheckedLocked()` 总会接收 HAL 的 release fence，并根据结果选择以下路径：

- 缓冲区正常且时间戳有效时，调用 `queueBuffer()` 交给 `Surface` 消费方；
- 缓冲区状态为错误、流正在丢帧或时间戳为 0 时，调用 `cancelBuffer()`；
- 两条路径都会携带 HAL release fence，保证下游或队列在 HAL 停止访问后再处理该缓冲区。

正常入队后，BufferQueue 中的这个栅栏从消费方视角又称为 acquire fence：消费方要等它发出信号后才能读取新图像。这是同一个同步对象跨越接口后发生的命名变化，并没有额外生成一条相机栅栏。

### 3.5 消费方释放后才能再次出队

消费方用完缓冲区后，会把 release fence 交回 BufferQueue。下一轮生产方通过 `dequeueBuffer()` 取得该队列槽位（slot）时，会同时拿到表示消费方完成时间的栅栏。CameraService 再把它放入 HAL 的 acquire fence 字段，缓冲区生命周期由此进入下一轮。

完整顺序可以写成：

```text
consumer release fence
        ↓
BufferQueue dequeueBuffer()
        ↓
HAL acquire fence → HAL wait/write
        ↓
HAL release fence
        ↓
BufferQueue queueBuffer()
        ↓
consumer acquire/wait/read
```

判断栅栏方向时，要同时写明“谁准备读或写”和“谁已经结束访问”。只记 `acquire`、`release` 两个名字，很容易在 HAL 接口与 BufferQueue 接口之间说反。

## 4. Android 17 的 HAL 缓冲区管理路径

Android 10 引入了可选的 HAL3 缓冲区管理 API。HAL 处理流水线可以同时排队 N 个捕获请求，但可能只在接近输出的阶段需要少量缓冲区。如果系统框架在请求进入 HAL 前便为所有输出取齐缓冲区，暂时用不到的图像内存也会长时间驻留。

Android 17 同时保留两类行为：

- 未启用的流：系统框架仍随捕获请求提供真实的输出缓冲区；
- 已启用的流：捕获请求中只有流的占位信息，`buffer` 为空，HAL 稍后再调用 `requestStreamBuffers()`。

在 `SESSION_CONFIGURABLE` 模式下，HAL 可以通过 `HalStream.enableHalBufferManager` 逐流选择；在 AIDL 设备级模式下，系统框架会把全部输出流视为由 HAL 管理。

### 4.1 `requestStreamBuffers()` 取得的缓冲区不绑定特定帧

Android 17 的 `AidlCamera3OutputUtils.cpp` 明确说明：一次 `requestStreamBuffers()` 返回的缓冲区不与某个 `CaptureRequest` 预先绑定。HAL 可以：

1. 为多条流批量请求若干缓冲区；
2. 选择其中一个用于某一帧；
3. 把已使用的缓冲区随该帧的 `processCaptureResult()` 返回；
4. 把多取但未使用的缓冲区经 `returnStreamBuffers()` 退回。

CameraService 会逐条流检查：

- 流是否存在且启用了 HAL 缓冲区管理；
- 是否重复请求同一个流 ID；
- `Surface` 是否已断开；
- “当前尚未归还数 + 本次请求数”是否超过 `maxBuffers`；
- 当前是否正在 `configureStreams()`。

可能的结果包括 `STREAM_DISCONNECTED`、`NO_BUFFER_AVAILABLE`、`MAX_BUFFER_EXCEEDED` 与 `FAILED_CONFIGURING`。`requestStreamBuffers()` 是同步调用，AIDL 注释建议 HAL 使用专用线程，并避免在延迟敏感的路径中一次请求大量缓冲区。

### 4.2 `bufferId` 与句柄缓存

每帧都跨 Binder 重复传递原生句柄（native handle）会增加开销。Android 17 的 `StreamBuffer` 采用 `streamId + bufferId` 建立缓存约定：

- 某个缓冲区第一次交给 HAL 时，同时携带 `bufferId` 和原生句柄；
- HAL 记住两者的映射；
- 同一个缓冲区后续再次出现时，只传 `bufferId`，句柄为空；
- `CaptureResult` 返回时句柄也为空，系统框架根据帧、流和缓冲区记录找回原对象；
- `processCaptureRequest(..., cachesToRemove)` 要求 HAL 删除已经失效的缓存项。

流被移除、会话关闭或系统框架通知删除缓存项后，HAL 不能继续使用旧映射。若把 `bufferId` 当作跨会话稳定的句柄，可能造成对象释放后仍被使用、缓冲区错配或设备错误。

### 4.3 `returnStreamBuffers()` 只归还未用于结果的缓冲区

HAL 已把缓冲区用于某帧时，应随 `processCaptureResult()` 返回。只有多取或预取后未使用的缓冲区，才通过 `returnStreamBuffers()` 归还。CameraService 找回相应的处理中缓冲区后，会用错误状态和时间戳 0 将其交还输出流，最终调用 `cancelBuffer()`，不会把它作为有效图像送给消费方。

### 4.4 `signalStreamFlush()` 与 `flush()` 的区别

两个接口都会促使缓冲区返回，但语义不同：

| 接口 | 目的 | 待处理请求的处理 |
|---|---|---|
| `signalStreamFlush()` | 为流的重新配置回收 HAL 手中的缓冲区 | HAL 应正常完成已有请求，并及时归还指定流的缓冲区 |
| `flush()` | 尽快清空整个捕获流水线 | 允许把未完成缓冲区标为 `ERROR`，返回时不得再有尚未完成的请求或尚未归还的缓冲区 |

`signalStreamFlush()` 是异步提示，`streamConfigCounter` 用来判断它是否晚于相应的 `configureStreams()` 到达。HAL 不能只根据 Binder 调用的到达顺序判断配置代次。

## 5. 三组同步栅栏不能混为一谈

Camera 预览上屏时，至少要区分下面三组同步：

| 同步边界 | 完成了什么 | 常见等待方 |
|---|---|---|
| 系统框架 → HAL acquire fence | 上一个消费方已停止使用输出缓冲区 | Camera HAL、ISP |
| HAL → 消费方 release fence | 传感器、ISP、HAL 已完成当前图像写入 | BufferQueue 消费方、`ImageReader`、编解码器、应用 GPU |
| SurfaceFlinger、HWC 的 release fence 与 present fence | 显示系统何时停止读取图层缓冲区，以及显示帧何时真正呈现 | BufferQueue 生产方、显示性能分析工具 |

显示系统的 present fence 不能证明相机输出已经完成；分析流或 JPEG 缓冲区也可能从未进入显示系统。反过来，HAL release fence 已发出信号，只能证明相机生产方完成写入，不表示 SurfaceFlinger 已经锁存（latch）该缓冲区，更不表示面板已经呈现这一帧。

在内核 `android17-6.18-2026-06_r6` 中，`dma_fence` 表示异步工作的完成点，`sync_file` 负责把一个或多个栅栏封装成文件描述符。Camera AIDL 传递的是原生句柄中的 fence fd；厂商 ISP、GPU、编解码器和显示驱动怎样创建栅栏并发出信号，需要回到相应设备的驱动与 HAL 源码核对。

## 6. 多输出的内存与背压

### 6.1 每路输出单独计算，整个会话共同受限

粗略估算相机图像内存时，应按流求和。下面的公式只用于估计缓冲区驻留量的数量级：

```text
session GraphicBuffer 驻留量
  ≈ Σ（该 stream 已分配 buffer 数 × allocator 返回的单 buffer 大小）
```

这只是排查起点。单个缓冲区的大小还受步幅、平面对齐、压缩元数据、保护属性、分块布局（tile layout）与厂商分配器影响；HAL、ISP 固件、GPU 和编解码器的内部工作缓冲区，也不一定出现在 CameraService 的流统计中。

常见格式的未压缩有效载荷（payload）可以用来检查数量级：

| 格式 | 可见像素数据的粗略量级 | 注意事项 |
|---|---:|---|
| RGBA_8888 | `width × height × 4` | 步幅与压缩会改变物理分配 |
| YUV 4:2:0 | `width × height × 1.5` | 平面步幅与切片高度不能省略 |
| RAW10 | `width × height × 1.25` | 行打包与对齐由实现决定 |
| RAW12 | `width × height × 1.5` | 同上 |
| RAW14 | `width × height × 1.75` | Android 17 能力仍要查询设备特性 |

`IMPLEMENTATION_DEFINED` 不能套用固定的每像素字节数。BLOB 流还要遵守配置中的 `bufferSize` 边界，不能把 JPEG 文件大小当作 `GraphicBuffer` 的分配大小。

### 6.2 处理缓慢的消费方怎样形成背压

每路输出都有独立队列，但一次捕获请求可以同时要求多个输出。当消费速度跟不上生产速度时，队列逐渐占满并反向阻塞上游，这就是背压（backpressure）。下面几种情况都会让缓冲区回收变慢：

- `ImageReader` 取得 `Image` 后没有及时 `close()`；
- CameraX `ImageProxy` 未关闭；
- 视频编码器输入拥塞；
- `TextureView` 所在应用长时间不绘制或不消费 `SurfaceTexture`；
- `Surface` 被销毁或进入废弃（abandoned）状态；
- 自研 OpenGL 或 Vulkan 渲染器长时间持有输入 `AHardwareBuffer`；
- SurfaceFlinger 或 HWC 长时间占用预览缓冲区。

由系统框架管理缓冲区时，只要某个目标流达到 HAL 的持有上限，`RequestThread` 就可能在取得该路缓冲区时等待。HAL 缓冲区管理模式提前了请求提交时机，HAL 则必须自行控制流水线深度，并处理 `requestStreamBuffers()` 暂时取不到缓冲区的情况。

多路输出是否互相拖慢，还取决于厂商实现的处理流水线。设备可能共享传感器读出通道、ISP 处理阶段、缩放器、带宽或内部缓冲池。看到分析流积压后预览也掉帧时，只能先把分析流列为候选原因；还要用帧编号、各路结果的返回时间与缓冲区归还记录证明因果关系。

### 6.3 应用侧最重要的归还动作

以下示例用于展示 `ImageReader` 消费图像时最基本的资源释放边界：

```kotlin
imageReader.setOnImageAvailableListener({ reader ->
    val image = reader.acquireLatestImage() ?: return@setOnImageAvailableListener
    try {
        analyze(image)
    } finally {
        image.close()
    }
}, analysisHandler)
```

`acquireLatestImage()` 适合只关心最新数据的分析任务，它可以丢弃较旧图像；只有调用 `image.close()`，当前缓冲区才会归还队列。若业务要求逐帧处理，可以改用 `acquireNextImage()`，但处理能力必须跟得上输入速率，并把 `maxImages` 视为可同时持有的图像数量上限。

## 7. 16 KB 页大小与 ION：纠正常见误解

### 7.1 16 KB 页大小并非 Android 17 首次引入

AOSP 从 Android 15 起支持 16 KB 页大小（page size）。它主要影响内核页粒度、`mmap()` 映射取整、ELF 文件对齐，以及依赖固定 `PAGE_SIZE` 的原生代码。Android 17 延续了这项兼容能力。

Camera AIDL、`GraphicBuffer` 和 BufferQueue 没有规定：

- 每个相机缓冲区的逻辑宽高必须按 16 KB 对齐；
- 图像有效载荷大小必须是 16 KB 的整数倍；
- 应用或 Camera HAL 应手工把 gralloc 分配结果补齐到 16 KB。

物理页、IOMMU 映射、平面步幅、内存堆粒度和硬件块对齐属于不同层次。内存分配器与驱动可能因为 16 KB 内核产生不同的物理占用，但不能由此推出统一的 Camera HAL 缓冲区对齐公式。排查时应读取 mapper 返回的布局、dma-buf 大小和设备内存堆配置。

### 7.2 Android 17 不再支持 ION

Android 17 AOSP 发布说明要求删除厂商代码中的 ION 调用。Android 12 的 GKI 2.0（通用内核映像）已经用 DMA-BUF heaps（共享缓冲区堆）取代 ION；到 Android 17，所有支持 ION 的内核都已结束维护。

因此 Android 17 camera 路径应按以下对象理解：

- gralloc 图形内存分配器决定 `GraphicBuffer` 的实现与布局；
- DMA-BUF heaps 或厂商分配器提供可共享的内存分配；
- dma-buf 文件描述符让 HAL、GPU、编解码器、HWC 等组件共享同一块分配；
- dma-fence 与 sync_file 文件描述符传递访问完成关系。

`ashmem` 也不是 Android 17 相机 `GraphicBuffer` 的可选“内存类型”。它用于普通共享内存，不提供 Camera HAL 图形流所需的 gralloc 元数据、用途标志协商和设备导入语义。

## 8. SurfaceView、TextureView 与自研预览的回收路径

### 8.1 SurfaceView

Camera HAL 完成缓冲区写入后，`Camera3OutputStream` 会直接将它送入 `Surface` 队列。SurfaceFlinger 为预览维护独立图层，HWC（硬件合成器）再决定使用 `CLIENT` 客户端合成还是 `DEVICE` 设备合成。缓冲区何时释放，取决于 SurfaceFlinger 或 HWC 是否仍在读取该图层。

这种路径省去了宿主应用逐帧采样相机纹理的工作，但宿主窗口与预览图层的几何位置、裁剪、透明度、圆角和可见性仍需协调。预览缓冲区提前到达，不代表图层事务已经在同一个显示帧中生效。

### 8.2 TextureView

相机缓冲区先进入 `SurfaceTexture`。应用的 HWUI 在绘制宿主窗口时取得它，再把预览纹理采样到应用窗口中。这里至少有两条队列，下面的结构图展示相机输入与应用窗口输出的先后关系：

```text
Camera HAL → SurfaceTexture
App HWUI   → App Window → SurfaceFlinger
```

第一条队列收到新相机帧后，还要等待应用主线程、`RenderThread`、GPU 和第二条队列。SurfaceFlinger 通常只能看到宿主应用的图层，因此不能只看图层树判断 Camera HAL 是否迟到。

### 8.3 自研 OpenGL 或 Vulkan

在滤镜、增强现实（AR）、畸变矫正或图像分割场景中，应用渲染器会先消费相机缓冲区，再生成一张新的可见缓冲区。性能分析必须分成以下阶段：

1. Camera HAL 写入以及对应的 release fence；
2. 应用 GPU 等待、采样和执行算法渲染轮次（pass）；
3. 渲染器把结果送入输出 `Surface` 的队列；
4. SurfaceFlinger 或 HWC 呈现图像。

只测量最终应用窗口的帧时间，会把相机输入迟到和应用 GPU 处理缓慢混在一起。

## 9. 出错、重配置与关闭时的所有权

### 9.1 缓冲区出错时也要保留栅栏语义

HAL 填充缓冲区失败时，会把状态设为 `ERROR`。如果它从未等待系统框架给出的 acquire fence，就要把该栅栏原样作为 release fence 返回；如果已经等待完成，则可以返回空的 release fence。发生错误并不意味着可以跳过同步。

CameraService 收到错误状态的缓冲区后会调用 `cancelBuffer()`。这会把队列槽位还给 BufferQueue，但仍要携带有效栅栏，防止队列过早复用该缓冲区。

### 9.2 Surface 断开是流的局部错误

应用销毁 `Surface`、`ImageReader` 或编解码器后，`requestStreamBuffers()` 可能得到 `STREAM_DISCONNECTED`，普通 `dequeueBuffer()` 也可能返回 `NO_INIT` 或 `DEAD_OBJECT`。HAL 应对涉及该流的请求报错，再由 CameraService 决定是否重建会话；任何一方都不能继续使用旧的缓冲区句柄。

### 9.3 `flush()` 返回后不得残留 HAL 缓冲区

AIDL `flush()` 约定返回时，HAL 中不能再有尚未完成的请求或尚未归还的缓冲区。此后系统框架才能安全地调用 `configureStreams()` 或提交新请求。关闭会话或移除流，还会终止 `bufferId` 缓存的有效期。

“相机已经关闭”应至少验证三件事：

- 重复请求已经停止，处理中的帧已经完成或报错；
- 所有输出和输入缓冲区都已返回；
- `Surface`、`Image`、编解码器与自研渲染器都没有继续持有旧对象。

## 10. 用 Perfetto 和 `dumpsys` 建立证据

### 10.1 记录会话配置

采集系统跟踪前，应记录：

- 相机 ID，以及逻辑相机与物理相机的关系；
- 每条流的 `Surface` 类型、格式、尺寸、色彩数据空间、帧率和动态范围；
- CameraX 版本，以及 `PreviewView` 实际选用的是 `SurfaceView` 还是 `TextureView`；
- `maxImages`、视频编码器配置和自研渲染器的输入输出；
- 是否启用 HAL 缓冲区管理，以及按设备还是按流启用；
- 厂商构建版本、Camera HAL、ISP 固件与内核版本。

缺少这些信息时，同一段 `dequeueBuffer()` 等待可能被误判成 gralloc 分配慢、消费方归还慢或 HAL 流水线处理慢。

### 10.2 按一帧的事件顺序检查

建议按照下面的事件顺序检查一帧：

```text
capture request / frame number
  → sensor timestamp / shutter
  → HAL output buffer result
  → HAL release fence
  → preview queueBuffer
  → SurfaceTexture acquire 或 SF latch
  → display present
```

分析、录像和静态拍照输出应分别建立时间线，不能用其中一路回调代替“预览已经就绪”的证据。HAL 缓冲区管理模式还要加入 `requestStreamBuffers()`、`bufferId` 与 `returnStreamBuffers()` 事件。

### 10.3 AOSP 能直接提供的线索

Android 17 CameraService 源码包含以下可核对点：

- `Camera3Device::RequestThread`：提交请求、按流取得缓冲区；
- `Camera3OutputStream::getBufferLockedCommon()`：`dequeueBuffer()` 或系统框架 BufferManager 路径；
- `Camera3Stream::getBuffer()`：等待 `max_buffers` 的时长；
- `Camera3OutputStream::returnBufferCheckedLocked()`：`queueBuffer()`、`cancelBuffer()` 与 HAL release fence；
- `AidlCamera3OutputUtils.cpp` 中的 `requestStreamBuffers()`：逐流校验 HAL 的缓冲区请求；
- 流的转储信息中，`DequeueBuffer latency histogram` 与 `wait on max_buffers` 两项统计。

设备系统跟踪中是否包含完整的相机、ISP、V4L2、IOMMU 或带宽轨道，由厂商实现决定。看不到厂商事件时，只能把问题定位到系统框架与 HAL 的接口边界，不能据此断言某个 ISP 硬件模块的耗时。

### 10.4 常见现象与下一步

| 现象 | 优先检查 | 不能直接下的结论 |
|---|---|---|
| `dequeueBuffer()` 长时间等待 | 消费方是否归还、`Surface` 是否断开、队列是否达到上限 | 一定是 gralloc 分配慢 |
| `requestStreamBuffers()` 返回 `NO_BUFFER_AVAILABLE` | 尚未归还的数量、`maxBuffers`、消费方持有时间 | HAL 发生内存泄漏 |
| `ImageReader` 延迟持续增长 | 图像的取得与关闭、`maxImages`、分析耗时 | 传感器帧率不稳 |
| `SurfaceView` 已入队但没有换帧 | HAL 栅栏、SurfaceFlinger 锁存、HWC 与呈现时间 | Camera HAL 没有产出 |
| `TextureView` 输入已到但屏幕显示晚 | `SurfaceTexture` 取得时间、应用主线程、`RenderThread`、GPU、宿主输出队列 | SurfaceFlinger 丢帧 |
| dma-buf 总量增长 | 各流数量、分配大小、HAL、ISP、编解码器内部缓冲区 | Java 堆内存泄漏 |

### 10.5 缓冲区阻塞不自动等于 ANR

缓冲区不足可能让 CameraService 的 `RequestThread`、HAL 专用线程或应用的同步调用进入等待。Android ANR 仍要求应用主线程、广播、服务或输入事件等路径超过相应的超时阈值。要证明两者存在因果关系，必须找到主线程或关键 Binder 调用等待相机操作的调用栈，再对齐缓冲区与栅栏的阻塞时间。

## 11. 检查清单

### HAL 与厂商实现

- [ ] `maxBuffers` 与流水线的并发持有量一致；
- [ ] 每次写入缓冲区前都等待 acquire fence；
- [ ] 结果返回 release fence 后不再访问缓冲区；
- [ ] HAL 缓冲区管理不超过每条流的上限；
- [ ] `bufferId` 缓存能处理 `cachesToRemove`、重新配置与关闭；
- [ ] `signalStreamFlush()` 使用 `streamConfigCounter` 处理乱序；
- [ ] `flush()` 返回前已归还所有请求和缓冲区；
- [ ] Android 17 厂商代码不再调用 ION；
- [ ] 4 KB 与 16 KB 内核上都没有硬编码 `PAGE_SIZE` 假设。

### 系统框架与应用

- [ ] 明确每个输出 `Surface` 的直接消费方；
- [ ] `Image` 或 `ImageProxy` 在所有异常路径中都能关闭；
- [ ] `TextureView` 与 `SurfaceView` 的性能证据分开采集；
- [ ] 自研渲染器的相机输入与可见输出分开计时；
- [ ] 用内存分配大小和缓冲区数量计算驻留量，不用分辨率乘以固定的每像素字节数代替；
- [ ] 诊断记录包含帧编号、流 ID、缓冲区 ID、传感器时间戳与栅栏；
- [ ] ANR 结论有主线程或关键 Binder 等待栈支持。

## 12. Android 10—17 的版本边界

| 版本 | 相关变化 |
|---|---|
| Android 10（API 29） | 引入可选的 Camera HAL3 缓冲区管理 API，HAL 可按需请求输出缓冲区 |
| Android 12（API 31） | GKI 2.0 以 DMA-BUF heaps 取代 ION，HAL3 请求—结果模型与 `Surface` 队列主线不变 |
| Android 13（API 33） | 新设备的 Camera HAL 接口开发转向 AIDL；HIDL 设备仍受兼容支持 |
| Android 15（API 35） | AOSP 开始支持 16 KB 页大小；它不是 Camera HAL3 的独有能力 |
| Android 16（API 36） | 继续完善 16 KB 兼容检查，缓冲区生命周期约定没有改变 |
| Android 17（API 37） | 平台源码锚点更新到 Android 17；AIDL 流级 HAL 缓冲区管理、缓冲区缓存和 `flush()` 约定均按 `android-17.0.0_r1` 核对；ION 不再受支持 |

## 13. Android 17 源码入口

- [`Camera3Device.cpp`](https://android.googlesource.com/platform/frameworks/av/+/android-17.0.0_r1/services/camera/libcameraservice/device3/Camera3Device.cpp)：`RequestThread`、系统框架与 HAL 的缓冲区管理分支、流刷新；
- [`Camera3Stream.cpp`](https://android.googlesource.com/platform/frameworks/av/+/android-17.0.0_r1/services/camera/libcameraservice/device3/Camera3Stream.cpp)：`max_buffers` 限流和未归还缓冲区统计；
- [`Camera3OutputStream.cpp`](https://android.googlesource.com/platform/frameworks/av/+/android-17.0.0_r1/services/camera/libcameraservice/device3/Camera3OutputStream.cpp)：`Surface` 配置、出队、入队或取消与栅栏处理；
- [`AidlCamera3OutputUtils.cpp`](https://android.googlesource.com/platform/frameworks/av/+/android-17.0.0_r1/services/camera/libcameraservice/device3/aidl/AidlCamera3OutputUtils.cpp)：`requestStreamBuffers()` 和 `returnStreamBuffers()`；
- [`StreamBuffer.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/camera/device/aidl/android/hardware/camera/device/StreamBuffer.aidl) 与 [`HalStream.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/camera/device/aidl/android/hardware/camera/device/HalStream.aidl)：缓冲区 ID、句柄、栅栏、`maxBuffers` 与逐流管理约定；
- [`ICameraDeviceCallback.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/camera/device/aidl/android/hardware/camera/device/ICameraDeviceCallback.aidl) 与 [`ICameraDeviceSession.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/camera/device/aidl/android/hardware/camera/device/ICameraDeviceSession.aidl)：缓冲区请求与归还、缓存删除、流刷新提示与 `flush()`；
- [`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp) 与 [`BufferQueueConsumer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp)：槽位状态，以及生产方和消费方的栅栏；
- [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c) 与 [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：内核栅栏与文件描述符封装；
- [Camera HAL3 buffer management APIs](https://source.android.com/docs/core/camera/buffer-management-api)、[16KB page size](https://source.android.com/docs/core/architecture/16kb-page-size/16kb) 与 [Android 17 release notes](https://source.android.com/docs/whatsnew/android-17-release)：版本和接口语义。

## 总结

排查相机缓冲区问题时，应先回答“哪条流、哪个消费方、谁正在持有缓冲区、正在等待哪一条栅栏”。系统框架管理模式会在请求进入 HAL 前从 `Surface` 取得缓冲区；HAL 缓冲区管理模式把取缓冲区的时机延后，但仍受同一个 `Surface` 队列、`maxBuffers` 和消费方回收速度约束。

一帧预览的 HAL release fence、BufferQueue 消费方取得缓冲区、SurfaceFlinger 锁存和显示系统呈现，分属不同阶段。录像、分析和静态拍照又各有自己的缓冲池，因此只看某个回调或一条图层轨道，无法解释整个相机会话。只有对齐帧编号、流 ID、缓冲区 ID、传感器时间戳、栅栏和消费方释放时间，才能区分 HAL 或 ISP 处理缓慢、缓冲区不足、应用持有过久和显示链路迟到。
