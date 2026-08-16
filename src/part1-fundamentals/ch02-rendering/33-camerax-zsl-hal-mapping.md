---
title: "CameraX ZSL 与 HAL Reprocessing Request 的映射关系"
chapter: "2.33"
section: "2.33"
status: ready-for-review
applicable_versions: "CameraX 1.2.0 - 1.6.1; Android 6.0 (API 23) - Android 17 (API 37)"
tags: [camerax, zsl, camera2, camera-pipe, hal3, reprocessing, android-17]
related_chapters: ["2.32", "13.9"]
last_verified: "2026-07-25"
last_verified_against: "CameraX 1.6.1 + android-17.0.0_r1 + android17-6.18-2026-06_r6"
confidence: high
sources:
  - type: androidx
    path: "camera-camera2/androidx/camera/camera2/adapter/ZslControl.kt"
  - type: androidx
    path: "camera-camera2/androidx/camera/camera2/adapter/CaptureConfigAdapter.kt"
  - type: androidx
    path: "camera-camera2/androidx/camera/camera2/adapter/CameraInfoAdapter.kt"
  - type: androidx
    path: "camera-camera2/androidx/camera/camera2/impl/CameraGraphConfigProvider.kt"
  - type: androidx
    path: "camera-camera2-pipe/androidx/camera/camera2/pipe/compat/Camera2CaptureSequenceProcessor.kt"
  - type: androidx
    path: "camera-core/androidx/camera/core/MetadataImageReader.java"
  - type: androidx
    path: "camera-core/androidx/camera/core/internal/utils/ZslRingBuffer.java"
  - type: androidx
    path: "camera-core/androidx/camera/core/internal/utils/ArrayRingBuffer.java"
  - type: aosp
    path: "frameworks/base/core/java/android/hardware/camera2/CameraDevice.java"
  - type: aosp
    path: "frameworks/base/core/java/android/hardware/camera2/CaptureRequest.java"
  - type: aosp
    path: "frameworks/base/core/java/android/hardware/camera2/CameraCharacteristics.java"
  - type: aosp
    path: "frameworks/av/services/camera/libcameraservice/device3/Camera3Device.cpp"
  - type: aosp
    path: "frameworks/av/services/camera/libcameraservice/device3/aidl/AidlCamera3Device.cpp"
  - type: aosp
    path: "hardware/interfaces/camera/device/aidl/android/hardware/camera/device/CaptureRequest.aidl"
  - type: aosp
    path: "hardware/interfaces/camera/device/aidl/android/hardware/camera/device/StreamBuffer.aidl"
  - type: aosp
    path: "kernel/common/drivers/dma-buf/dma-fence.c"
  - type: aosp
    path: "kernel/common/drivers/dma-buf/sync_file.c"
  - type: official
    path: "https://developer.android.com/media/camera/camerax/take-photo/zsl"
  - type: official
    path: "https://developer.android.com/jetpack/androidx/releases/camera"
  - type: writer
    path: "Writer/rendering_pipelines/S11_camera_type.md"
---

# 2.33 CameraX ZSL 与 HAL Reprocessing Request 的映射关系

CameraX 的零快门延迟（Zero Shutter Lag，ZSL）模式会持续保留最近拍摄的 `PRIVATE` 图像；`PRIVATE` 表示像素布局由设备实现，应用不直接读取。用户按下快门时，如果缓存中存在满足条件的图像，CameraX 会把该图像和同一时间戳的 `TotalCaptureResult`（完整捕获结果）送入 Camera2 可重处理会话，再请求设备输出 JPEG。相机不需要为这次请求重新曝光，因此照片内容可以来自按键之前。

这里的“零延迟”只描述快门动作与源图像时刻之间的目标。JPEG 编码、回调调度和文件写入仍然需要时间，ZSL 也不承诺每次拍照都使用历史帧。

以下讨论以 CameraX 稳定版 `1.6.1`、Android 17（API 37）的 `android-17.0.0_r1` 标签和内核 `android17-6.18-2026-06_r6` 为验证边界。分析 ZSL 路径时，需要把握四条规则：

1. CameraX ZSL 依赖 `PRIVATE_REPROCESSING` 能力、合法的输入/输出配置和当前用例（UseCase）组合，不能只看 `CAPTURE_MODE_ZERO_SHUTTER_LAG`；
2. CameraX 1.6.1 的 ZSL 环形队列（ring）固定保留 3 个合格的 `ImageProxy`，没有图像清晰度评分、运动补偿或可配置的 5—10 帧缓存；
3. CameraX 显式重处理与 `CONTROL_ENABLE_ZSL` 所代表的设备内部 ZSL 是两条不同路径；
4. 到达 Camera HAL AIDL 边界后，只有有效的 `CaptureRequest.inputBuffer` 才能证明该请求是重处理请求（reprocess request）。

## 1. ZSL 减少的是哪一段时间

一次普通静态拍照可以简化为以下过程：

```text
按下快门
  → 提交 still capture request
  → 等待 sensor 曝光
  → ISP / 厂商算法处理
  → JPEG 输出
  → CameraX 回调
  → 应用写文件
```

这张时序只用于划分时间段。普通拍照的源帧通常产生于按键之后，因此曝光以及自动对焦、自动曝光、自动白平衡这三项状态的收敛，都可能增加用户感知到的延迟。

CameraX ZSL 的成功路径是：

```text
持续 repeating request
  → PRIVATE output + TotalCaptureResult
  → 按 timestamp 匹配图像和 metadata
  → 过滤 AF / AE / AWB 状态
  → 3 帧 ring

按下快门
  → 取出一帧及其 TotalCaptureResult
  → ImageWriter.queueInputImage()
  → CameraDevice.createReprocessCaptureRequest()
  → JPEG output
  → CameraX 回调
  → 应用写文件
```

这里省去了“按键后再取得一张传感器图像”这一步。重处理、JPEG 编码、回调和存储仍在按键之后执行。使用按键前的源帧也会带来取舍：照片记录的时刻可能早于用户触摸事件，运动主体的位置未必与按键瞬间一致。

## 2. 先区分两种都叫 ZSL 的机制

Android Camera2 同时暴露了设备内部 ZSL 和应用管理的 ZSL。名称相近，控制方式和证据不同。

| 机制 | 控制入口 | 历史帧由谁保留 | HAL 请求特征 | 是否保证使用历史帧 |
|---|---|---|---|---|
| 设备内部 ZSL | `CONTROL_ENABLE_ZSL=true`，且捕获意图为 `STILL_CAPTURE` | Camera HAL 或厂商流水线 | 仍可能是没有输入缓冲区的普通捕获请求 | 不保证 |
| 应用管理的 ZSL | 可重处理会话、缓存图像、`createReprocessCaptureRequest()` | CameraX 或 Camera2 客户端 | 请求带有有效输入缓冲区 | 缓存和提交成功时使用该输入缓冲区 |

Android 17 的 `CaptureRequest.CONTROL_ENABLE_ZSL` 文档只说明设备“可以启用”内部 ZSL。即使键值为 `true`，设备也可以不选择历史帧；输出内容对应的 `SENSOR_TIMESTAMP` 还可能早于之前的普通请求。

`CameraDevice.TEMPLATE_ZERO_SHUTTER_LAG` 面向应用管理的 ZSL。CameraX 1.6.1 也把这个模板类型用作捕获配置的意图标记：`CaptureConfigAdapter` 看到它后，会尝试从环形队列取出输入图像。成功时，CameraPipe 调用 `createReprocessCaptureRequest(totalCaptureResult)`；环形队列没有可用帧时，配置会改用普通静态拍照模板。

看到 `TEMPLATE_ZERO_SHUTTER_LAG`，只能说明上层希望使用 ZSL；看到 `CONTROL_ENABLE_ZSL=true`，只能说明设备获准尝试内部 ZSL。确认显式重处理时，还要检查输入流和输入缓冲区。

## 3. `isZslSupported()` 是设备能力预筛选

下面的示例用于在构建 `ImageCapture` 前选择拍照模式：

```kotlin
@OptIn(ExperimentalZeroShutterLag::class)
fun buildImageCapture(cameraInfo: CameraInfo): ImageCapture {
    val captureMode = if (cameraInfo.isZslSupported) {
        ImageCapture.CAPTURE_MODE_ZERO_SHUTTER_LAG
    } else {
        ImageCapture.CAPTURE_MODE_MINIMIZE_LATENCY
    }

    return ImageCapture.Builder()
        .setCaptureMode(captureMode)
        .setFlashMode(ImageCapture.FLASH_MODE_OFF)
        .build()
}
```

这段代码只做能力选择。最终能否建立 ZSL 会话，还要等 CameraX 合并所有用例配置并检查流组合。

在 CameraX 1.6.1 的 Camera2 实现中，`CameraInfoAdapter.isZslSupported()` 主要检查两项：

- CameraCharacteristics 包含 `REQUEST_AVAILABLE_CAPABILITIES_PRIVATE_REPROCESSING`；
- 当前设备没有命中 `ZslDisablerQuirk` 兼容性特例。

API 文档还规定最低系统版本为 Android 6.0（API 23）。这个返回值不检查当前闪光灯模式、`VideoCapture`、Camera Extension 和分辨率策略，也不验证本次会话最终选中的所有 `Surface` 能否同时配置。

可以把判定分成三层：

| 层次 | 典型检查 | 失败结果 |
|---|---|---|
| 设备能力 | API 23 及以上、支持 `PRIVATE_REPROCESSING`、无禁用兼容性特例 | 不宣称支持 ZSL |
| 会话配置 | `PRIVATE` 输入尺寸有效、支持 `PRIVATE → JPEG`、用例组合可配置 | 不建立重处理输入流 |
| 单次拍照 | 闪光灯为 `OFF`、环形队列中存在带完整元数据的合格帧 | 改用普通静态拍照 |

### 3.1 CameraX 1.6.1 的禁用条件

以下情况会禁用或绕过 CameraX ZSL：

- 绑定 `VideoCapture`；
- 启用 Camera Extension；
- 闪光灯模式为 `ON` 或 `AUTO`；
- 请求高分辨率优先模式，导致 `OPTION_ZSL_DISABLED` 被设置；
- 命中 `ZslDisablerQuirk` 设备特例；
- 设备没有 `PRIVATE_REPROCESSING`；
- `StreamConfigurationMap` 没有可用的 `PRIVATE` 输入尺寸；
- `getValidOutputFormatsForInput(PRIVATE)` 不包含 JPEG；
- 拍照时环形队列为空，或其中没有可用的元数据。

闪光灯的处理需要单独说明。CameraX 可以保留已经建立的可重处理会话，只在闪光灯为 `ON` 或 `AUTO` 时提交普通静态拍照；用户切回 `OFF` 后，无需仅为这一变化重建整个会话。用例配置、设备能力或兼容性特例不允许 ZSL 时，`ZslControlImpl` 会跳过输入流的建立。

CameraX 1.6.1 的兼容性特例列表包含若干 Samsung Fold4、S22、S24 型号和 Xiaomi Mi 8，原因是重处理图像可能出现颜色异常或变焦冻结。机型名单属于库版本的实现细节，升级 CameraX 后应重新检查相应版本的 `ZslDisablerQuirk`。

## 4. 会话怎样完成配置

### 4.1 输入格式固定为 `PRIVATE`

`ZslControlImpl` 把 ZSL 格式固定为 `ImageFormat.PRIVATE`。它从：

```text
StreamConfigurationMap.getInputSizes(ImageFormat.PRIVATE)
```

选择面积最大的输入尺寸，然后确认：

```text
getValidOutputFormatsForInput(ImageFormat.PRIVATE)
```

包含 `ImageFormat.JPEG`。

这些查询解决两个不同问题：

- 输入尺寸决定哪一种 `PRIVATE` 图像可以送回设备；
- 输入/输出格式映射决定这种输入能否重处理成 JPEG。

`PRIVATE` 表示应用不读取图像的像素布局。CameraX 持有的是 `Image` 与 `GraphicBuffer` 句柄以及元数据，设备端按照实现定义的缓冲区契约处理。不能用“宽 × 高 × 固定每像素字节数”精确计算这批缓冲区的物理内存。

### 4.2 同一个会话中同时存在输出与输入

CameraX 会创建一个 `MetadataImageReader`，把它的 `Surface` 加入重复请求的输出目标。这路输出会持续接收可作为候选帧的 `PRIVATE` 图像。

CameraX 还会为会话设置宽、高和格式相同的 `InputConfiguration`。Camera2 建立可重处理捕获会话后，会话会暴露一个输入 `Surface`。CameraPipe 在这个输入 `Surface` 上创建 `ImageWriter`，供拍照时把候选图像送回相机设备。

结构可以画成：

```text
regular repeating request
  ├─ preview output → PreviewView / Surface
  └─ ZSL PRIVATE output → MetadataImageReader → ZslRingBuffer

selected PRIVATE Image
  → ImageWriter → session input Surface
  → reprocess request
  → JPEG output Surface
```

上半部分仍是传感器采集，下半部分以已有缓冲区为输入，不再触发新的传感器曝光。

## 5. 环形队列中保存了什么

### 5.1 图像必须先与元数据按时间戳匹配

`MetadataImageReader` 同时监听 `ImageReader` 和 `CameraCaptureCallback`。图像与 `CameraCaptureResult` 的到达顺序可能不同，它会根据时间戳把二者配成一个带有 `ImageInfo` 的 `ImageProxy`。

只有匹配成功后，`ZslRingBuffer` 才能读取相应的 AF、AE、AWB 状态。图像和捕获结果长时间无法匹配时，旧数据会被清理；不能把“`ImageReader` 回调到达”当成“环形队列中已有可重处理帧”。

### 5.2 CameraX 1.6.1 只接纳三自动状态合格的帧

`ZslRingBuffer.isValidZslFrame()` 的条件是：

- AF（自动对焦）为 `LOCKED_FOCUSED` 或 `PASSIVE_FOCUSED`；
- AE（自动曝光）为 `CONVERGED`；
- AWB（自动白平衡）为 `CONVERGED`。

任一条件不满足，`ImageProxy` 都会立即关闭，不会进入环形队列。这只是依据枚举状态过滤元数据，没有分析图像内容。弱光下 AE 长时间不收敛、连续对焦扫描、快速切换场景或元数据缺失，都可能让环形队列为空。

### 5.3 三个容易混淆的数量

CameraX 1.6.1 源码中出现了三个含义不同的缓冲区数量：

| 名称 | 数值 | 约束对象 |
|---|---:|---|
| `RING_BUFFER_CAPACITY` | 3 | 可供 ZSL 选择的合格 `ImageProxy` 数量 |
| `ZslControlImpl.MAX_IMAGES` | 9 | 传给 `MetadataImageReader` 的图像上限，源码中为环形队列容量的 3 倍 |
| CameraPipe 输入端 `maxImages` | 1 | 会话输入 `Surface` 上的 `ImageWriter` 并发图像数 |

“ZSL 缓存 3 帧”不代表整个相机处理流水线只分配 3 个 `GraphicBuffer`。预览、JPEG、ZSL 输出、HAL 处理中的缓冲区、`ImageReader` 和输入流各有自己的队列约束，驻留量要逐条流统计。

### 5.4 当前实现没有“最佳帧评分器”

`ZslRingBuffer` 继承自 `ArrayRingBuffer`。新帧通过 `addFirst()` 加入，`dequeue()` 通过 `removeLast()` 取出；容量已满时，会先移除并关闭队尾最旧的帧。

由此得到 CameraX 1.6.1 的准确行为：

1. 监听器每次通过 `acquireLatestImage()` 取得当时最新的已匹配图像；
2. 图像先经过 AF、AE、AWB 过滤；
3. 环形队列最多持有 3 帧；
4. 拍照时取出当前队列里最早保留的合格帧。

`ImageCapture` API 注释把目标概述为交付时间戳接近快门的中间结果，但 1.6.1 的这段实现没有按触摸时间遍历候选，也没有清晰度评分或运动补偿。排查具体版本时，应以该版本源码和实测 `SENSOR_TIMESTAMP` 为准。

## 6. 从 CameraX 请求映射到 Camera2 重处理请求

CameraX 1.6.1 的 Camera2 后端已经迁移到 CameraPipe。较早资料中常见的 `androidx.camera.camera2.internal.*` 路径不能直接代表这个版本；对应的核心实现位于 `androidx.camera.camera2.adapter` 和 `androidx.camera.camera2.pipe.compat`。

### 6.1 `CaptureConfigAdapter` 生成 `InputRequest`

当捕获配置的模板为 `TEMPLATE_ZERO_SHUTTER_LAG`，并且用例和闪光灯设置没有禁用 ZSL 时，`CaptureConfigAdapter` 会尝试从环形队列取出一帧。

取帧成功后，它完成三件事：

1. 从 `ImageProxy.imageInfo` 取回匹配的 `CameraCaptureResult`；
2. 把底层 `Image` 包装为 CameraPipe 的图像对象；
3. 把图像与相应的 `FrameInfo` 组合成 `InputRequest`。

如果环形队列为空，`inputRequest` 会保持为空，CameraX 随后把请求模板改为普通的 `TEMPLATE_STILL_CAPTURE`。环形队列中的帧已经完成元数据匹配；若内部图像与结果的类型或非空约束被破坏，源码会在构造 `InputRequest` 时失败，不能把这种异常当作普通降级。

### 6.2 `ImageWriter` 把缓冲区送入会话输入端

CameraPipe 会为可重处理会话的输入 `Surface` 创建 `ImageWriter`。准备提交请求时，`Camera2CaptureSequenceProcessor` 先调用以下方法，把选中的历史帧排入输入队列：

```text
imageWriter.queueInputImage(selectedImage)
```

这一步把 CameraX 持有的 `PRIVATE` 图像排入 Camera2 会话的输入队列。它没有复制出一张可由应用访问的位图，也没有把 JPEG 数据送回 HAL。

### 6.3 `TotalCaptureResult` 初始化重处理请求

CameraPipe 从 `FrameInfo` 中解包同一源帧的 `TotalCaptureResult`，再调用以下方法创建重处理请求：

```text
cameraDevice.createReprocessCaptureRequest(totalCaptureResult)
```

设备需要原始捕获结果中的曝光、白平衡、镜头、裁剪和厂商元数据，才能按照源图像的拍摄条件进行重处理。Android Camera2 要求输入图像来自同一台相机设备，并在同一个会话中直接或间接产生；随意组合其他相机或其他会话的图像与结果，不符合接口约定。

创建请求构建器后，CameraPipe 会添加本次静态拍照的目标 `Surface`，通常是 CameraX 图像流水线的 JPEG 输出端，并写入 JPEG 方向、质量等请求参数。

### 6.4 生命周期必须覆盖成功、失败和取消

被选中的 `ImageProxy` 在排入 `ImageWriter` 后仍持有底层资源。CameraX 会为请求安装监听器，并在以下路径中通过同一个原子引用关闭它：

- 请求完成；
- 请求失败；
- 请求中止；
- 完整捕获结果到达。

多个回调可能先后发生，原子引用可以保证资源只关闭一次。若自行实现 Camera2 ZSL，也要在提交失败、会话关闭、请求中止和异常路径中完整回收输入图像。

失败边界分为两种：如果拍照时没有候选帧，CameraX 会改用普通静态拍照；如果已经构造 `InputRequest`，随后 `ImageWriter.queueInputImage()` 或 `createReprocessCaptureRequest()` 失败，CameraPipe 会让本次捕获序列构建失败。不能假定这一阶段仍会自动重试普通拍照。

## 7. Android 17 系统框架如何识别重处理请求

Camera2 请求进入 CameraService 后，`Camera3Device` 会根据请求元数据中的输入流 ID 找到 `mInputStream`。`RequestThread` 在提交 HAL 前从 `Camera3InputStream` 取得下一块输入缓冲区，并填入以下原生请求字段：

```text
camera_capture_request_t.input_buffer
camera_capture_request_t.input_width
camera_capture_request_t.input_height
```

如果请求没有输入流，`input_buffer` 为 `NULL`。这个分支决定请求是新的传感器采集，还是对已有图像进行重处理。

CameraService 的 AIDL 适配层再把原生请求转换为 `android.hardware.camera.device.CaptureRequest`：

- `inputBuffer.streamId` 标识输入流；
- `inputBuffer.bufferId` 标识该流中的缓冲区；
- 首次出现的缓冲区还会携带句柄，后续可以只使用 `bufferId`；
- `inputBuffer.acquireFence` 约束 HAL 何时可以读取输入缓冲区；
- `inputWidth` 与 `inputHeight` 描述实际输入尺寸；
- `outputBuffers[]` 至少包含一个待写入的目标缓冲区。

AIDL `CaptureRequest.aidl` 直接规定：

- 无有效 `inputBuffer`：从成像设备捕获新图像；
- 有有效 `inputBuffer`：重处理该图像；
- HAL 必须等待输入 acquire fence 后再读取；
- HAL 必须在后续 `CaptureResult` 中归还输入缓冲区；
- 输出缓冲区也有各自的 acquire fence、release fence 和所有权转换。

这就是 CameraX ZSL 到 Camera HAL3 的可靠映射：

```text
CameraX InputRequest
  → Camera2 reprocess CaptureRequest
  → Camera3Device::CaptureRequest.mInputStream
  → camera_capture_request_t.input_buffer
  → AIDL CaptureRequest.inputBuffer
  → HAL reprocessing
```

HAL 内部重新经过 ISP 的哪些处理模块、是否使用专用硬件、怎样执行降噪或 JPEG 编码，都属于设备实现。公共接口只约束输入缓冲区、元数据、输出缓冲区、栅栏、结果和错误行为，不能根据接口名称推断厂商算法阶段。

## 8. 缓冲区、同步栅栏与背压

### 8.1 ZSL 输出也会占用相机流缓冲区

环形队列保存的是尚未关闭的 `ImageProxy`。每保留一帧，就有一块 `PRIVATE` 输出缓冲区无法回到生产方队列。队列满后会关闭被淘汰的帧，拍照完成或失败后会关闭被选中的帧，会话重置时则会清空全部帧。

如果图像没有按预期关闭，可能出现：

- `MetadataImageReader` 达到 `maxImages`；
- ZSL 输出流没有空闲缓冲区；
- 重复请求被输出端背压拖慢；
- 预览、分析或其他共享 camera 资源出现连带延迟。

这类问题要按照 [Camera HAL3 Buffer 管理](./32-camera-hal3-buffer-management.md)中的方法逐条流检查。预览正常不能证明 ZSL 输出流和输入队列正常。

### 8.2 输入缓冲区的所有权跨过 HAL

调用 `ImageWriter.queueInputImage()` 后，输入 `Surface` 的消费方变为 CameraService 与 HAL 路径。HAL 读取前要等待 acquire fence，完成访问后再通过捕获结果和 release fence 归还缓冲区。在 release fence 发出信号前，客户端不能安全地复用该缓冲区。

内核的 `dma-fence` 和 `sync_file` 只提供同步原语；CameraX 的三帧策略、AF、AE、AWB 过滤、降级条件和重处理元数据都位于用户空间。分析 ZSL 失败时，不应先把业务策略归因于内核。

### 8.3 重处理请求不读取传感器

Android 17 的 `CameraDevice` 文档明确规定，重处理请求不会捕获新的图像数据。它从会话输入 `Surface` 取得下一块缓冲区，再为本次请求的输出 `Surface` 生成结果。

这也解释了两个常见现象：

- 输出 JPEG 的 `SENSOR_TIMESTAMP` 可以早于按键时间；
- 重处理仍可能等待输入队列、HAL 流水线、JPEG 输出缓冲区或同步栅栏；源帧已经存在，并不代表回调会立即返回。

## 9. 如何验证设备上是否走了 ZSL

### 9.1 记录应用层条件

每次拍照至少记录：

- CameraX 版本；
- 相机 ID；
- `CameraInfo.isZslSupported()`；
- 拍照模式；
- 闪光灯模式；
- 已绑定的用例；
- Camera Extension 是否启用；
- 目标分辨率策略；
- `SENSOR_INFO_TIMESTAMP_SOURCE`；
- 按键的 `elapsedRealtimeNanos()`；
- 输出图像或捕获结果的传感器时间戳；
- 成功、失败和错误码。

不能只记录一个 `zsl=true` 布尔值。它无法说明会话是否建立了输入流，也无法说明本次拍照是否从环形队列中取得了历史帧。

### 9.2 检查 CameraX 日志

CameraX 1.6.1 源码中可直接定位的诊断文本包括：

- `Private reprocessing isn't supported`；
- `Unable to find a supported size for ZSL`；
- `JPEG isn't valid output for ZSL format`；
- `Selected ZSL size`；
- `No such element`；
- `Queuing image ... for reprocessing to ImageWriter`；
- `Failed to create a ReprocessingCaptureRequest.Builder`。

前三项用于说明能力或会话配置，`No such element` 表示拍照时环形队列中没有帧；最后两项才接近单次重处理请求的提交阶段。

### 9.3 用 `dumpsys media.camera` 查看输入流

`Camera3Device::dump()` 会输出当前的流配置、输入流，以及最近一次请求的输入流与输出流 ID。它适合回答以下问题：

- 会话是否配置了输入流；
- 最近的请求是否引用输入流；
- 输出流是否仍然存在；
- 设备当前是活动状态还是错误状态。

`dumpsys` 提供的是当前状态快照。短请求已经完成或会话已经重建时，快照可能错过目标事件，因此应与带时间戳的应用日志、CameraService 日志或 Perfetto 系统跟踪配合使用。

### 9.4 HAL 侧以 `inputBuffer` 为准

厂商可以在 `processCaptureRequest()` 入口记录：

- 帧编号；
- 输入流 ID 与缓冲区 ID；
- 输入 acquire fence；
- 输出流 ID 与缓冲区 ID；
- 请求设置是否来自 FMQ（快速消息队列）；
- 归还输入与输出缓冲区时的 release fence 和状态。

有效的输入缓冲区说明这是重处理请求。没有输入缓冲区但 `CONTROL_ENABLE_ZSL=true`，只说明设备可以尝试内部 ZSL；两种证据不能相互替代。

### 9.5 延迟要区分源帧年龄与完成时间

建议分别统计下面三个量；变量名保留英文，便于直接用于日志和分析脚本：

```text
source_age = shutter_event_time - sensor_timestamp
callback_latency = callback_time - shutter_event_time
save_latency = file_complete_time - callback_time
```

这三个量回答的问题不同。`source_age > 0` 表示图像来自按键前，但不能证明回调很快。`callback_latency` 包含重处理、JPEG 编码和调度时间；`save_latency` 主要属于应用收到结果后的文件 I/O 路径。

只有 `SENSOR_INFO_TIMESTAMP_SOURCE_REALTIME` 才能把 `SENSOR_TIMESTAMP` 直接与 `elapsedRealtimeNanos()` 比较。时间戳来源为 `UNKNOWN` 时，两者可能不属于同一个时钟域，必须先在设备上完成校准，不能直接计算 `source_age`。

## 10. 常见误判

| 误判 | 源码对应的修正 |
|---|---|
| ZSL 一定走 HAL 重处理 | 条件满足且本次环形队列中有可用帧时，才会构造 `InputRequest` |
| `isZslSupported()` 为 `true` 就一定生效 | 它没有检查闪光灯、`VideoCapture`、Camera Extension、高分辨率偏好和本次流配置 |
| CameraX 会缓存 5—10 帧并动态调节 | 1.6.1 的环形队列容量常量为 3 |
| CameraX 从候选中做清晰度评分和运动补偿 | 1.6.1 只检查 AF、AE、AWB 枚举状态 |
| `CONTROL_ENABLE_ZSL=true` 就是重处理请求 | 设备内部 ZSL 可以没有输入缓冲区 |
| `TEMPLATE_ZERO_SHUTTER_LAG` 能证明 HAL 收到输入图像 | 模板只表示上层意图；HAL 侧还要检查 `inputBuffer` |
| ZSL 能把整次拍照压到固定毫秒数 | 设备、场景、JPEG、线程调度和存储都会改变完成时间 |
| 环形队列只有 3 帧，所以内存就是 3 个缓冲区 | 图像读取器、输入流、预览流、JPEG 流和 HAL 处理中缓冲区都有各自的队列 |
| 重处理会重新曝光一次 | Camera2 接口约定不会捕获新的图像数据 |
| 重处理失败总会自动重试普通拍照 | 取帧前可以降级；排入输入端后的失败不能假定存在透明重试 |

## 11. 评审清单

### CameraX 与应用

- [ ] 依赖版本固定为 CameraX 1.6.1，源码路径按 CameraPipe 后端核对；
- [ ] 使用 `CameraInfo.isZslSupported()` 做设备能力预筛选；
- [ ] 闪光灯保持 `OFF`；
- [ ] 未同时启用 VideoCapture 或 Camera Extension；
- [ ] 高分辨率策略没有禁用 ZSL；
- [ ] 拍照日志记录拍照模式、用例、闪光灯和 Camera Extension 状态；
- [ ] 统计 `SENSOR_TIMESTAMP` 与快门事件时间，不用回调时间代替拍摄时间；
- [ ] 对普通拍照降级和重处理提交失败分别统计。

### 系统框架与 HAL

- [ ] `PRIVATE_REPROCESSING` 能力与流配置一致；
- [ ] `PRIVATE` 输入尺寸有效；
- [ ] `PRIVATE → JPEG` 是合法重处理格式组合；
- [ ] 会话配置了输入流；
- [ ] 输入图像与 `TotalCaptureResult` 来自同一台相机设备和同一个会话；
- [ ] 重处理请求带有有效输入缓冲区和至少一个输出缓冲区；
- [ ] HAL 等待输入和输出 acquire fence；
- [ ] HAL 在捕获结果中归还输入与输出缓冲区和 release fence；
- [ ] 失败、`flush()`、重新配置和关闭路径不会遗留输入缓冲区；
- [ ] 通过帧编号、流 ID、缓冲区 ID、传感器时间戳和栅栏关联各层证据。

## 12. 版本边界

| 版本 | 相关边界 |
|---|---|
| Android 6.0（API 23） | Camera2 可重处理会话、`createReprocessCaptureRequest()` 和 `ImageWriter` 能力成为 CameraX ZSL 的系统基础 |
| CameraX 1.2.0 | `CAPTURE_MODE_ZERO_SHUTTER_LAG` 作为实验 API 引入 |
| Android 14（API 34） | 重处理请求的 `CONTROL_CAPTURE_INTENT` 默认设为 `STILL_CAPTURE`；更早版本需要调用方自行留意 |
| CameraX 1.6.0 | Camera2 后端迁移到 CameraPipe，排障时应使用新的 adapter 与 pipe 实现路径 |
| CameraX 1.6.1 | 库侧锚点；固定 3 帧环形队列、`PRIVATE` 重处理、当前兼容性特例和降级逻辑均按该版本源码核对 |
| Android 17（API 37） | 平台源码锚点；Camera2 重处理、Camera3 输入流与 AIDL `CaptureRequest.inputBuffer` 均按 `android-17.0.0_r1` 核对 |

CameraX 是独立于 Android 系统发布的 Jetpack 库。同一台 Android 17 设备可以运行不同的 CameraX 版本，因此分析报告必须同时写明系统源码标签、厂商构建版本和 CameraX 版本。

## 13. 源码入口

### CameraX 1.6.1

- [`ZslControl.kt`](https://dl.google.com/dl/android/maven2/androidx/camera/camera-camera2/1.6.1/camera-camera2-1.6.1-sources.jar)：`PRIVATE` 输入、3 帧环形队列、9 个读取器图像上限、能力检查和会话配置；
- [`CaptureConfigAdapter.kt`](https://dl.google.com/dl/android/maven2/androidx/camera/camera-camera2/1.6.1/camera-camera2-1.6.1-sources.jar)：从环形队列生成 `InputRequest`，以及没有输入时改用普通静态拍照；
- [`CameraInfoAdapter.kt`](https://dl.google.com/dl/android/maven2/androidx/camera/camera-camera2/1.6.1/camera-camera2-1.6.1-sources.jar)：`isZslSupported()` 的 Camera2 实现；
- [`Camera2CaptureSequenceProcessor.kt`](https://dl.google.com/dl/android/maven2/androidx/camera/camera-camera2-pipe/1.6.1/camera-camera2-pipe-1.6.1-sources.jar)：`ImageWriter`、`createReprocessCaptureRequest()` 和请求提交；
- [`MetadataImageReader.java`](https://dl.google.com/dl/android/maven2/androidx/camera/camera-core/1.6.1/camera-core-1.6.1-sources.jar)：图像与结果的时间戳匹配；
- [`ZslRingBuffer.java`](https://dl.google.com/dl/android/maven2/androidx/camera/camera-core/1.6.1/camera-core-1.6.1-sources.jar) 与 [`ArrayRingBuffer.java`](https://dl.google.com/dl/android/maven2/androidx/camera/camera-core/1.6.1/camera-core-1.6.1-sources.jar)：三自动过滤、容量与 FIFO 取帧；
- [CameraX ZSL 指南](https://developer.android.com/media/camera/camerax/take-photo/zsl)与 [CameraX release notes](https://developer.android.com/jetpack/androidx/releases/camera)：公开能力、限制和版本历史。

### Android 17

- [`CameraDevice.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/hardware/camera2/CameraDevice.java)：可重处理会话、模板和 `createReprocessCaptureRequest()` 约定；
- [`CaptureRequest.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/hardware/camera2/CaptureRequest.java)：设备内部 `CONTROL_ENABLE_ZSL` 语义；
- [`CameraCharacteristics.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/hardware/camera2/CameraCharacteristics.java)：`PRIVATE_REPROCESSING` 与流配置映射；
- [`Camera3Device.cpp`](https://android.googlesource.com/platform/frameworks/av/+/android-17.0.0_r1/services/camera/libcameraservice/device3/Camera3Device.cpp)：输入流创建、输入缓冲区获取和 HAL 请求组装；
- [`AidlCamera3Device.cpp`](https://android.googlesource.com/platform/frameworks/av/+/android-17.0.0_r1/services/camera/libcameraservice/device3/aidl/AidlCamera3Device.cpp)：原生请求到 AIDL 输入/输出缓冲区的转换；
- [`CaptureRequest.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/camera/device/aidl/android/hardware/camera/device/CaptureRequest.aidl) 与 [`StreamBuffer.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/android-17.0.0_r1/camera/device/aidl/android/hardware/camera/device/StreamBuffer.aidl)：重处理判定、缓冲区 ID、句柄与栅栏约定；
- [`dma-fence.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/dma-fence.c) 与 [`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c)：缓冲区栅栏的内核同步基础。

## 总结

CameraX ZSL 是一条有前提条件的显式重处理路径。CameraX 1.6.1 持续接收 `PRIVATE` 输出，把图像与捕获结果按时间戳配对，只保留 AF 已对焦且 AE、AWB 已收敛的帧，再从容量为 3 的环形队列中取出一帧。拍照时，CameraPipe 通过 `ImageWriter` 把这帧送入会话的输入 `Surface`，并用同一帧的 `TotalCaptureResult` 创建重处理请求。

在 Android 17 CameraService 与 HAL AIDL 的边界上，是否存在有效的 `inputBuffer`，决定请求是重处理还是新的传感器采集。模板名、拍照模式和 `CONTROL_ENABLE_ZSL` 都不足以单独证明这一点。排障时，应分层记录设备能力、会话配置、单次取帧、输入缓冲区、输出缓冲区、时间戳与同步栅栏，才能解释某次拍照为何使用历史帧、为何降级，或者为何在重处理阶段失败。
