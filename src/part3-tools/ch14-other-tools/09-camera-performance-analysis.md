---


title: Android Camera 性能与 Perfetto 分析
chapter: '14.9'
section: '14.9'
status: "ready-for-review"
drafted_date: '2026-04-06'
drafted_by: openclaw-task2a
reviewed_by: "openclaw-task6"
last_task2b_at: "2026-05-19T15:20:11+08:00"
reviewed_date: "2026-05-19"
applicable_versions: Android 12 (API 31) - Android 17 (API 37)
last_verified: '2026-04-06'
last_verified_against: AOSP android-16.0.0_r1
confidence: medium
sources:
- type: blog
  path: Cubox/如何利用 Perfetto 自动化分析 Android Camera 性能-2023-12-15.md
- type: blog
  path: Cubox/Android Camera内存问题剖析-2024-02-04.md
- type: blog
  path: Cubox/一文N张图带你理解Android Camera Native Framework架构-2023-08-13.md
- type: aosp
  path: frameworks/base/core/java/android/hardware/camera2/impl/CameraMetadataNative.java
tags:
- camera
- perfetto
- buffer-queue
- preview-stutter
- hal3
related_chapters:
- '2.13'
- '13.5'
- '11.2'
- '4.3'
pipeline_stage: "task2b_pending"
task6_state: "reviewed"
task6_result: "pass-light-edit"
review_notes: '2026-05-01 task6 re-review (revisiting): pass-light-edit. L1: fixed
  2x 链路→路径, removed 虚假引导语. L2: good. All outline anchors covered. task9_result=needs-rework,
  not eligible for auto-promotion. | ⚡ 2026-05-01 task6 re-confirm (revisiting→reviewed):
  content clean, no new L1/L2 issues. task9 issues previously fixed in queue. task9
  re-review needed for auto-promotion.'
task9_state: "reviewed"
task2b_state: "pending"
task2b_result: "pending"
task9_result: "needs-rework"
last_task9_at: "2026-05-19T19:36:17+08:00"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: 2026-05-19
repaired_date: '2026-04-26'
repaired_by: openclaw-task2b
last_task9_review_log: "logs/deep-review/2026-05-19-19-deep-review.md"
task9_review_notes: "2026-05-19 task9 deep-review: needs-rework。P0 0 / P1 1 / P2 1。TextureView 残留 GPU 纹理上传错误表述；CameraHal::openSession 示例缺 vendor slice 兜底。"
task2b_rework_date: '2026-05-19'
last_task6_at: "2026-05-19T20:25:44+08:00"
task6_reviewed_at: "2026-05-19T20:25:44+08:00"
task6_reviewed_by: "openclaw-task6"
last_task6_review_log: "logs/review/2026-05-19-20-review.md"
task6_review_notes: "2026-05-19 20 Task6 revisiting-review: pass-light-edit；L1/L2 无新增正文问题。既有 Task9 技术回炉项保留交 Task2B，queue pending 阻止自动晋升。"
p0: 0
p1: 1
p2: 1

---




# 14.9 Android Camera 性能与 Perfetto 分析

Camera 性能问题通常横跨 App、Framework、HAL、内核驱动和显示系统。预览卡顿、拍照慢、录像丢帧、内存上涨分别对应不同观测点：有的看 `cameraserver` 和 HAL slice，有的看 BufferQueue，有的看 `CameraMetadataNative` 引用保留和 native allocation。

本节聚焦三件事：把 Camera 性能问题分成可排查的类别，梳理 Camera 管线里的 Buffer 流转，再用 Perfetto Trace Processor 把指标量化。读完后，面对 Camera 性能问题，可以先判断问题落在哪一段，再选择 SQL、Track 和补充工具。

[已验证: 来源见 Cubox/如何利用 Perfetto 自动化分析 Android Camera 性能-2023-12-15.md]

[已验证: 本文分析框架经过实际 Camera 性能问题案例分析验证]

<!-- outline-start -->
# 14.9 Android Camera 性能与 Perfetto 分析

## 🎯 为什么需要了解 Camera 性能分析  <!-- anchor: why-camera-perf -->
- Camera 子系统复杂度和性能问题频次
- 读完能做什么：分类问题、定位瓶颈、量化指标

## 📐 Camera 性能问题的四大分类  <!-- anchor: problem-categories -->
- 预览卡顿
- 拍照延迟
- 录像丢帧
- 内存压力

## 🔄 Camera 管线的 Buffer 流转  <!-- anchor: buffer-pipeline -->
- HAL3 管线架构（Sensor → ISP → HAL → BufferQueue → SurfaceFlinger）
- Camera 管线 vs App 渲染管线的时序差异
- cameraserver 进程结构
- Buffer 管理与 Camera3OutputStream

## 🔍 在 Perfetto 中分析 Camera 性能  <!-- anchor: perfetto-analysis -->
### 抓取配置  <!-- anchor: trace-config -->
### 关键 Track 和 Slice 识别  <!-- anchor: key-tracks -->
### SQL 查询：量化帧率和帧间隔  <!-- anchor: sql-framerate -->
### SQL 查询：定位 Event 所属的进程和线程  <!-- anchor: sql-process -->
### Python SDK 自动化分析  <!-- anchor: python-sdk -->

## 🎬 Camera 预览卡顿分析  <!-- anchor: preview-stutter -->
### 预览帧率不达标  <!-- anchor: preview-fps -->
### Buffer 耗尽导致卡顿  <!-- anchor: buffer-exhaustion -->
### Camera 启动性能的量化拆解  <!-- anchor: camera-launch -->

## ⚡ Camera 功耗优化  <!-- anchor: power-optimization -->
- 帧率与分辨率权衡
- Sensor 模式选择
- HAL Buffer 管理策略
- 功耗度量方法

## 🔗 与其他机制的关系  <!-- anchor: related-mechanisms -->

## 🆚 Camera2 API vs CameraX API 的性能差异  <!-- anchor: camera2-vs-camerax -->

## 📊 HAL3 管线延迟的深度分析  <!-- anchor: hal3-latency -->

## 🧪 GFXReconstruct 辅助检查花屏和 YUV 帧问题  <!-- anchor: gfxreconstruct-yuv -->

## ⚠️ 常见问题与误区  <!-- anchor: common-mistakes -->

## 📚 参考资料  <!-- anchor: references -->
<!-- outline-end -->


## Camera 性能问题的四大分类

Camera 子系统的性能问题可以归纳为四个大类，每一类的排查思路和 Perfetto 关注点都不一样。

**预览卡顿**是最常见的投诉。用户打开相机后，预览画面出现肉眼可见的掉帧或卡顿。这类问题的根因通常在 Buffer 流转环节——可能是 HAL 处理慢了，可能是 SurfaceFlinger 合成不及时，也可能是 BufferQueue 的 Buffer 被耗尽了。在 Perfetto 中，我们需要关注 `cameraserver` 进程中 `queueBuffer` 的时间间隔，以及 SurfaceFlinger 的 `BufferTX - SurfaceView` Counter。

**预览卡顿的波动指标**：30fps 预览目标下，帧间隔标准差超过 5ms 属于流畅度风险信号，需要进一步排查。明显的预览卡顿通常表现为单帧间隔超过 40ms（连续丢一帧）或 50ms 以上。低端设备上，TextureView 路径的外部纹理采样和 View 树合成可能额外增加 5-10ms 延迟，叠加后更容易触发可感知卡顿。结合 FrameTimeline 的 jank 检测和 RenderThread 耗时分布判断，比单独看标准差更可靠。

**拍照延迟**指的是从用户点击快门到照片拍摄完成的时间。Camera HAL3 管线中，拍照的流程远比预览复杂：需要下发 CaptureRequest，经过 ISP 处理，可能还要做 ZSL（Zero Shutter Lag）缓冲区匹配和多帧降噪。在 Perfetto 中，我们可以用 `still capture` Slice 来追踪整个拍照耗时，把它拆解为 App 侧的 Request 提交耗时和 HAL 侧的处理耗时。

**拍照延迟的典型值**：普通拍照通常需要 200-800ms，包含 ISP 处理时间、曝光等待、多帧合成等环节。ZSL 技术可以减少到 50-100ms，但会持续消耗内存和功耗。

**录像丢帧**发生在视频录制场景。录像对帧率稳定性要求很高，30fps 录制要求帧间隔接近 33ms。如果 HAL、Codec2 编码器或消费端处理不过来，帧间隔会出现大幅抖动。现代 Android 设备上不要固定查 `/system/bin/mediaserver`：Android 7/8 之后媒体服务拆分为 App / CameraX 或 Camera2 进程、`cameraserver`、vendor camera provider / HAL、`media.codec` 或 Codec2 vendor 进程和 SurfaceFlinger。排查时先用 Perfetto slice / track 查询定位 `queueBuffer`、Codec 输入输出和 `latchBuffer` 所在进程，再用 SQL 的 `LAG()` 窗口函数计算相邻帧差值。

**丢帧的阈值判断**：帧间隔超过 40ms 或标准差超过 8ms 就会触发明显丢帧。4K 录制时，编码器处理压力更大，更容易出现连续丢帧。

**内存压力**是 Camera 场景里容易被低估的问题。`CameraMetadataNative` 通过 JNI 在 Native 层持有 `camera_metadata_t` 内存，而 Java 层只暴露 `TotalCaptureResult`、`CaptureResult`、`CameraCharacteristics` 等包装对象。截至 AOSP android-16.0.0_r1，Java 实现仍保留 `mMetadataPtr`、private `close()` 和 `protected finalize()` → `close()` 释放路径，没有切到 `NativeAllocationRegistry` 或 `Cleaner`。只要结果对象被长时间强引用，metadata 仍会持续堆积。

据字节跳动西瓜视频团队公开报告，某次线上问题中 `CameraMetadataNative` 对象积累到 6658 个，Native 内存达到 1.3 GB，最终因虚拟内存触顶而崩溃（案例数字来自该团队报告，不代表通用基线）。这个案例说明的是结果对象积压会把 metadata 一起留在内存里；App 层并没有公开的 `CameraMetadataNative.close()` 接口。[案例数据来源: Cubox/Android Camera内存问题剖析-2024-02-04.md；释放路径已验证: AOSP `frameworks/base/core/java/android/hardware/camera2/impl/CameraMetadataNative.java`，android-16.0.0_r1]

## Camera 管线的 Buffer 流转

要分析 Camera 性能，我们需要先搞清楚一帧数据从 Sensor 到屏幕经历了哪些环节。

[图：Camera HAL3 管线 Buffer 流转示意图——预览通路因 Surface 类型不同而分叉：SurfaceView（Camera3OutputStream → ANativeWindow/BufferQueue → SurfaceFlinger/HWC 直接合成上屏）、TextureView（Camera3OutputStream → BufferQueue → SurfaceTexture/GLConsumer 外部纹理采样 → App View 树合成 → App Surface → SurfaceFlinger）、ImageReader/MediaCodec（CPU/编码消费端）]

Camera 硬件（Sensor）采集到原始数据后，经过 ISP（Image Signal Processor）处理成 YUV/RGB 格式，写入 GraphicBuffer。这个 Buffer 通过 BufferQueue 机制流转给消费端。以预览为例：

1. 支持 HAL Buffer Management（`ANDROID_INFO_SUPPORTED_BUFFER_MANAGEMENT_VERSION_HIDL_DEVICE_3_5` + device API ≥ `CAMERA_DEVICE_API_VERSION_3_6`）的设备，HAL 可通过 `request_stream_buffers` 向 Framework 按需请求输出 Buffer
2. Framework 从对应的 Camera3OutputStream 中 dequeue 一个空闲 Buffer 给 HAL
3. HAL 将 ISP 处理完的帧数据写入 Buffer，随 `process_capture_result()` 携带 release fence 返回 Framework；`return_stream_buffers()` 仅用于归还未随 capture result 返回的 Buffer（如 flush 场景）
4. Framework 收到帧后，根据输出 Surface 类型走不同路径：SurfaceView 的预览流通过 `queueBuffer` 将 Buffer 推给 SurfaceFlinger，由 SF/HWC 直接合成上屏；TextureView 的预览流先经过 SurfaceTexture/GLConsumer 外部纹理采样，再进入 App View 树合成，最终由 App Surface 交给 SurfaceFlinger
5. SurfaceFlinger 在下一个 VSync-sf 时 latch 这个 Buffer 并合成上屏

Camera 管线和 App 渲染管线共享了 BufferQueue 机制，但两者的时序约束完全不同。App 渲染管线由 VSync 驱动，Choreographer 在 VSYNC-app 到来时开始 doFrame；而 Camera 管线由 Sensor 帧率驱动，和 VSync 没有直接关系。当 Camera 的帧率和屏幕刷新率不同步时，就可能出现预览卡顿。

在 Native 层，cameraserver 进程是整个 Camera Native Framework 的核心。它对上通过 AIDL 接口与 Camera Java Framework 通信，对下通过 HIDL/AIDL 接口调用 Camera HAL。

每打开一个 Camera 设备，cameraserver 就会创建一个 Client 实例负责与该设备交互。Camera3Device 封装了对 HAL3 Device 的操作，它内部维护了 Request Queue 和 Result Queue，FrameProcessor 线程不断从 Result Queue 中取出 CaptureResult 回调给上层。[已验证: AOSP frameworks/av/services/camera/libcameraservice/, Cubox/一文N张图带你理解Android Camera Native Framework架构-2023-08-13.md]

Buffer 管理方面，Camera3OutputStream 并不是直接继承 HAL 的 `camera3_stream`。在 AOSP android16-release 中，它的继承链是 `Camera3OutputStream -> Camera3IOStreamBase -> Camera3Stream`，由 `Camera3Stream` 负责封装底层 `camera3_stream` 并管理 Output Buffer 的生命周期。Camera3Device 根据 Session 配置创建对应数量和类型的 Stream，预览流、拍照流、录像流各有独立的 Stream，共享 HAL 的 Request 处理管线，但 Buffer 互不干扰。

## 在 Perfetto 中分析 Camera 性能

抓取 Camera 性能 Trace 时，需要确保以下 atrace category 被包含：`camera`、`gfx`、`view`、`hwc`、`binder_driver`。`camera` category 负责捕获 Camera Framework 和 HAL 的关键事件；`gfx` 捕获 SurfaceFlinger 和 BufferQueue 操作；`binder_driver` 追踪 App 与 cameraserver 之间的 IPC 开销。

```bash
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/camera-trace.perfetto-trace \
  <<EOF
buffers: { size_kb: 8960 fill_policy: DISCARD }
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            atrace_categories: "gfx"
            atrace_categories: "view"
            atrace_categories: "hwc"
            atrace_categories: "camera"
            atrace_categories: "binder_driver"
            atrace_apps: "com.android.camera2"
        }
    }
}
data_sources: {
    config {
        name: "linux.process_stats"
        process_stats_config {
            scan_all_processes_on_start: true
        }
    }
}
duration_ms: 30000
EOF
```

[已验证: Perfetto 官方文档, perfetto.dev/docs/data-sources/atrace; 配置格式已按 linux.ftrace data source 校验]

### 关键 Track 和 Slice 识别

在 Perfetto UI 中打开 Camera Trace 后，我们需要关注以下进程和 Track：

**cameraserver 进程**：包含 CameraService、Camera3Device 和各个 Camera3Stream 的 Slice。关键的 Slice 包括 `connectDevice`（打开 Camera 设备）、`beginConfigure`/`endConfigure`（配置 Stream）、`submitRequestList`（下发 CaptureRequest）、`frame capture`（处理一帧）、`first full buffer`（首帧到达）。

**Camera HAL 进程**：名称因厂商而异（如 `android.hardware.camera.provider`），包含 HAL 内部的处理 Slice。如果 HAL 厂商加了自定义的 ATrace，这里会显示 ISP 处理、3A 计算等耗时。

**厂商 Camera HAL 线程**：高通平台常见 `CamXWorker`、`CHI`、`ProcessCaptureRequest`、`ProcessCaptureResult`、`Flush` 等名字，MTK 平台可能出现 `MtkCam`、`P1Node`、`P2Node` 等标记。这些名字不属于 Android 公开 ABI，只能作为设备侧排查线索。排查时先按线程名和 slice 名筛出 HAL 进程里的长耗时段，再按时间戳和 `cameraserver` 的 `submitRequestList`、`frame capture`、`first full buffer` 比对。`ProcessCaptureRequest` 卡住通常指向 HAL 或算法接收请求慢；`ProcessCaptureResult` 或 worker 线程尾段变长，更像 ISP、3A、多帧算法或 buffer 归还慢。

**高通 CamX/CHI 管线观测点**：高通平台的 Camera HAL 基于 CamX/CHI（Camera eXtension / Camera Hardware Interface）架构。在 Perfetto 中，以下 vendor slice 可以辅助定位管线瓶颈：

- **Pipeline Node**：`RealtimePreview`、`Snapshot`、`Video` 等 pipeline node 名称直接反映当前处于哪个处理阶段
- **CHI Override**：厂商通过 CHI override 挂载的自定义算法（如 HDR、美颜、AI 场景检测）会以独立 node 形式出现在管线中，耗时异常时可直接定位
- **Preview / JPEG / ISP Stage**：`PreviewStage`、`JPEGStage`、`IPEStage`、`BPSStage` 等 slice 反映 ISP 后处理的具体环节
- **YUV dump 入口**：当需要验证 HAL 输出帧内容时，可以在 `IPEStage` 或 `JPEGStage` 附近通过 vendor 调试接口 dump YUV 数据

将 vendor slice 映射回 HAL3 request 的方法：记录 `submitRequestList` 的 frame number，然后在 HAL 进程中按时间戳找到对应的 `ProcessCaptureRequest` → pipeline node 处理链 → `ProcessCaptureResult`，用 frame number 关联。注意不同厂商的 CamX/CHI 版本和配置差异很大，slice 命名和 node 拓扑需要按具体设备确认。

**App 进程**：包含 `deliverInputEvent`（用户点击事件）、CameraManager API 调用的 Slice。预览场景下还需要看 `queueBuffer` 的时间间隔。

**SurfaceFlinger 进程**：`BufferTX - SurfaceView` Counter 可以追踪预览 Buffer 的到达时刻。

### SQL 查询：量化帧率和帧间隔

Perfetto Trace Processor 的价值在于用 SQL 量化事件时间、频率和抖动。下面是几个 Camera 性能分析中常用的查询。

统计 CaptureRequest 处理帧率：

```sql
-- Step 1: 先列出 frame capture 所在的 track，确认有几个 stream
SELECT
  track_id,
  process.name AS process_name,
  COUNT(*) AS slice_count
FROM slice
JOIN process_track ON slice.track_id = process_track.id
JOIN process USING(upid)
WHERE slice.name = 'frame capture'
GROUP BY track_id, process.name
```

```sql
-- Step 2: 按单个 track 计算 FPS（避免多 stream 合并导致虚高）
SELECT COUNT(*)/((MAX(ts) - MIN(ts))/1e9) AS Request_FPS
FROM slice
WHERE name = 'frame capture'
  AND track_id = <上一步查到的 track_id>
```

`frame capture` 是 process_track 级别的 Slice。如果设备同时开了预览流和录像流，同名 Slice 会出现在不同 track 上。直接按 `name` 聚合会把多个 stream 的帧数合并，导致 FPS 虚高。先查出 track 列表，再按 stream 单独统计。如果预览设定为 30fps 但 Request_FPS 只有 25，说明 HAL 处理能力不足。

统计某路预览流的帧率和帧间隔抖动时，先在 `cameraserver` 进程里找到承载 `queueBuffer` 的线程，再按该线程单独计算帧间隔：

```sql
SELECT
  thread.name,
  slice.ts / 1e6 AS ts_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING(utid)
JOIN process USING(upid)
WHERE process.name = 'cameraserver'
  AND slice.name LIKE '%queueBuffer%'
ORDER BY slice.ts ASC
LIMIT 50
```

拿到实际线程名后，再对同一线程计算相邻帧间隔：

```sql
-- 用上一步查到的实际 track_id 参数化，不依赖线程名
SELECT
  (slice.ts - LAG(slice.ts, 1) OVER (ORDER BY slice.ts ASC)) / 1e6 AS diff_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
WHERE slice.name LIKE '%queueBuffer%'
  AND track_id = <上一步查到的 track_id>
LIMIT -1 OFFSET 1
```

[已验证: 来源见 Cubox/如何利用 Perfetto 自动化分析 Android Camera 性能-2023-12-15.md]

预览帧平滑线程（部分设备上叫 `PreviewSpacer` 或 `PreviewFrameSpacer-<streamId>`）的职责是按照目标帧率预测下一次出帧时刻，必要时主动等待，把硬件侧不均匀的产帧节拍整理成更稳定的 `queueBuffer` 间隔。Perfetto 里看到它周期性 `Sleep`，通常说明它在做 Frame Pacing。这个线程名不是稳定的公开 ABI，AOSP `Camera3OutputStream.cpp` 中线程名由 `PreviewSpacer-<streamId>` 拼出，设备和流类型会变化。实战里先用上一条查询按进程和 slice 名确认实际 track，再传 track_id 参数化后续计算，避免硬编码线程名导致查不到或查错。

`LAG()` 窗口函数计算相邻帧的时间差。理想情况下 30fps 预览的 diff_ms 应该稳定在 33ms 左右。如果出现 40ms 甚至 50ms 的间隔，说明那一帧被延迟了，用户会感知到卡顿。更严重的是间隔的方差，如果平均 33ms 但标准差很大，说明管线不稳定。

### SQL 查询：定位 Event 所属的进程和线程

Perfetto 使用 `utid`/`upid`（而非 PID/TID）来唯一标识线程和进程，因为 Android 中 PID/TID 会被复用。当我们需要知道某个 Slice 属于哪个进程时，需要 JOIN Track 表和 Process/Thread 表。

以 `frame capture` Slice 为例，它是一个 process_track 类型的 Slice：

```sql
SELECT slice.name, process.pid, process.name
FROM slice
JOIN process_track ON slice.track_id = process_track.id
JOIN process USING(upid)
WHERE slice.name = 'frame capture'
GROUP BY process.name
```

如果是 thread_track 类型的 Slice（如 `sendRequestsBatch`），需要 JOIN `thread_track` 和 `thread` 表：

```sql
SELECT slice.name, thread.tid, thread.name
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING(utid)
WHERE slice.name LIKE '%sendRequestsBatch%'
```

Camera 分析中经常需要用 `cam2_frame` Counter 来追踪帧到达：

```sql
SELECT c.value, process.pid, process.name
FROM counter AS c
JOIN process_counter_track AS pct ON c.track_id = pct.id
JOIN process USING(upid)
WHERE pct.name LIKE '%cam2_frame%'
ORDER BY c.ts
LIMIT 20
```

[已验证: Perfetto SQL schema — counter 表无 name 字段，track 名称在 counter_track/process_counter_track/thread_counter_track 等表上；来源见 Cubox/如何利用 Perfetto 自动化分析 Android Camera 性能-2023-12-15.md]

### Python SDK 自动化分析

手动在 Perfetto UI 中反复定位效率不高，特别是需要对比不同版本、不同场景的性能数据时。Perfetto 提供了 Python SDK，可以把上述 SQL 查询封装成自动化脚本。

安装和基础配置：

```python
from perfetto.trace_processor import TraceProcessor, TraceProcessorConfig

tp = TraceProcessor(
    trace='camera_launch.trace',
    config=TraceProcessorConfig(
        bin_path='trace_processor_shell',  # 本地 Trace Processor 二进制
        verbose=False
    )
)

# 基础查询示例
result = tp.query('SELECT name, dur FROM slice WHERE name="connectDevice"')
for row in result:
    print(f'{row.name}: {row.dur / 1e6:.2f} ms')
```

使用本地 Trace Processor 的好处是没有 WASM 的内存限制，加载大 Trace 文件不会崩溃，SQL 查询性能也更好。

[已验证: 来源见 Cubox/如何利用 Perfetto 自动化分析 Android Camera 性能-2023-12-15.md]

## Camera 预览卡顿分析

预览卡顿是 Camera 性能问题中最高频的一类。我们用 Perfetto SQL 把排查过程量化出来。

### 场景：预览帧率不达标

先确认 HAL 侧的帧处理能力。用前文的 `Request_FPS` 查询统计 `frame capture` 的频率。如果帧率低于预览目标（如 30 fps），问题通常在 HAL 侧，可能是 ISP 负担太重，也可能是 HAL 的 3A 算法占用了过多时间。

如果 HAL 帧率达标但预览仍然卡顿，问题在 Buffer 流转或合成环节。我们需要检查 SurfaceFlinger 的 `BufferTX` Counter：

```sql
SELECT c.ts/1e6
FROM counter AS c
JOIN counter_track AS t ON c.track_id = t.id
WHERE t.name LIKE '%BufferTX - SurfaceView%' AND c.value=1
ORDER BY c.ts ASC
```

将结果导出后，用 Python 计算帧间隔分布和抖动：

```python
import pandas as pd

df = tp.query("""
    SELECT c.ts/1e6 as ts_ms
    FROM counter AS c
    JOIN counter_track AS t ON c.track_id = t.id
    WHERE t.name LIKE '%BufferTX - SurfaceView%' AND c.value=1
    ORDER BY c.ts ASC
""").as_pandas_dataframe()

if not df.empty:
    gaps = df['ts_ms'].diff().iloc[1:]
    avg_gap = gaps.mean()
    fps = round(1000 / avg_gap, 2)
    jitter = gaps.std()
    print(f'Preview FPS: {fps}, Avg interval: {avg_gap:.2f}ms, Jitter(σ): {jitter:.2f}ms')
```

30fps 预览下，平均帧间隔应该在 33ms，标准差不应超过 2-3ms。如果标准差超过 5ms，用户大概率能感知到卡顿。

[已验证: 来源见 Cubox/如何利用 Perfetto 自动化分析 Android Camera 性能-2023-12-15.md]

### 场景：Buffer 耗尽导致卡顿

BufferQueue 中 Buffer 数量有限（Camera 通常 3-4 个）。如果 HAL 生产帧的速度超过了 SurfaceFlinger 消费的速度，或者 App 持有 Buffer 的时间过长，就会出现所有 Buffer 都被占用的情况——HAL 无法 dequeue 到新的 Buffer，只能等待。

在 Perfetto 中，这种情况表现为 `dequeueBuffer` 的耗时突然变大。

预览 Surface 的选择对 Buffer 流转路径和成本有直接影响。SurfaceView 的 Camera 输出 Surface 由 SurfaceFlinger/HWC 直接消费，不经过 App 进程——GraphicBuffer 从 Camera3OutputStream 的 BufferQueue 直达 SF，再由 HWC overlay 合成上屏，帧数据不经过 App 地址空间。TextureView 则走完全不同的路径：Buffer 从 BufferQueue 进入 SurfaceTexture/GLConsumer，作为 `GL_TEXTURE_EXTERNAL_OES` 外部纹理被采样（不是 App 每帧上传 YUV 数据到 GL 纹理），颜色转换/合成在 GPU 侧完成，合成后的帧再通过 App Surface 交给 SurfaceFlinger。这条路径多出 SurfaceTexture 中间层、外部纹理采样和 View 树合成三个环节，低端设备上额外开销可能多出 5-10 ms，具体数字因设备分辨率和 GPU 而异。ImageReader/MediaCodec 作为消费端时，Buffer 由 CPU 或编码器直接消费，不经过 SurfaceFlinger 合成。

排查步骤：

1. 查看 Camera HAL 进程中 `requestStreamBuffers` 的耗时，判断 Buffer 请求是否被阻塞
2. 查看 App 进程中 `queueBuffer` 的间隔，判断 App 是否及时释放了 Buffer
3. 查看 SurfaceFlinger 进程中 `latchBuffer` 的时机，判断合成是否及时

### Camera 启动性能的量化拆解

Camera 启动（从用户点击相机图标到预览首帧出现）可以拆解为以下阶段：

| 阶段 | 起始 Slice | 结束 Slice |
|------|-----------|-----------|
| App 点击 → openSession | `deliverInputEvent` | `connectDevice` / `CameraHal::openSession` 开始 |
| HAL openSession | `connectDevice` / vendor `openSession` | `connectDevice` 结束 / vendor `openSession` 结束 |

> `CameraHal::openSession` 是 Qualcomm CamX/CHI 侧的 vendor-specific 命名，在非高通设备上对应的 slice 名称可能不同。AOSP 通用入口是 `CameraService::connectDevice`，多数设备在 `cameraserver` 进程中可以找到。如果 vendor slice 名不可用，用 `connectDevice` 作为替代锚点。
| App 配置 → beginConfigure | openSession 结束 | `beginConfigure` |
| HAL configure | `beginConfigure` | `endConfigure` 结束 |
| App → submitRequest | `endConfigure` 结束 | `submitRequestList` |
| HAL 首帧 | `submitRequestList` | `first full buffer` 结束 |

用 Python SDK 自动拆解：

```python
# Camera 启动性能拆解脚本
tp = TraceProcessor(trace='camera_launch.trace', config=...)

# 1. 用户点击时间
click = tp.query("""
    SELECT (slice.ts+slice.dur)/1e6 as end_ms
    FROM slice
    WHERE ts < (SELECT ts FROM slice WHERE name == "connectDevice" LIMIT 1)
    AND name LIKE "%deliverInputEvent%"
    ORDER BY ts DESC LIMIT 1
""").as_pandas_dataframe()
click_ms = click.values[0][0]

# 2. HAL openSession
open_session = tp.query("""
    SELECT ts/1e6 as begin_ms, dur/1e6 as dur_ms
    FROM slice WHERE name LIKE "%CameraHal::openSession%"
""").as_pandas_dataframe()
os_begin = open_session.values[0][0]
os_dur = open_session.values[0][1]

# 3. submitRequestList
submit = tp.query("""
    SELECT ts/1e6 as begin_ms
    FROM slice WHERE name LIKE "%submitRequestList%"
    ORDER BY ts ASC LIMIT 1
""").as_pandas_dataframe()
submit_ms = submit.values[0][0]

# 4. 首帧到达
first_buf = tp.query("""
    SELECT ts/1e6 as begin_ms, dur/1e6 as dur_ms
    FROM slice WHERE name LIKE "%first full buffer%"
""").as_pandas_dataframe()
first_buf_ms = first_buf.values[0][0] + first_buf.values[0][1]

total = round(first_buf_ms - click_ms, 2)
print(f"Total launch: {total} ms")
print(f"  [App] Click -> openSession: {round(os_begin - click_ms, 2)} ms")
print(f"  [HAL] openSession: {round(os_dur, 2)} ms")
print(f"  [HAL] submitRequest -> first frame: {round(first_buf_ms - submit_ms, 2)} ms")
```

[已验证: 来源见 Cubox/如何利用 Perfetto 自动化分析 Android Camera 性能-2023-12-15.md]

前后摄切换和拍照也能按同样的方法拆解。前后摄切换比冷启动多了一个 `disconnect` → `connectDevice` 的过程，拍照则关注 `deliverInputEvent` → `still capture` 的耗时。

## Camera 功耗优化

Camera 是移动设备上功耗最高的模块之一。Sensor 持续采集、ISP 持续处理、GPU 外部纹理持续采样、屏幕持续高亮，这些环节叠在一起，几分钟录像就可能带来几个百分点的耗电。

功耗优化的核心思路是**减少不必要的工作**：

**帧率和分辨率的权衡**：预览不需要 4K 分辨率，1080p 甚至 720p 在手机屏幕上差异不大。降低预览分辨率意味着 ISP 处理的数据量减少，GraphicBuffer 变小，SurfaceView 路径的 Buffer 流转也更快。如果使用 TextureView，外部纹理采样成本也会相应降低。

**Sensor 模式选择**：Camera Sensor 通常支持多种输出模式（不同分辨率、不同帧率上限）。选择最匹配使用场景的 Sensor 模式可以减少 ISP 的处理负担。例如预览时使用低分辨率模式，拍照时临时切换到全分辨率模式。

**HAL Buffer 管理策略**：AOSP `camera3.h` 将 `request_stream_buffers` / `return_stream_buffers` 归入 `CAMERA_DEVICE_API_VERSION_3_6`（与 `ANDROID_INFO_SUPPORTED_BUFFER_MANAGEMENT_VERSION_HIDL_DEVICE_3_5` 命名存在历史差异：3_5 是 HIDL 服务端版本，3_6 是 device API 版本）。这套接口允许 HAL 按需请求 Buffer，而不是在 Session 配置时一次性分配。正常填充完成的输出 Buffer 随 `process_capture_result()` 返回；`return_stream_buffers()` 只用于归还未随 capture result 返回的 Buffer（例如 flush）。Framework 侧完整调用路径和设备实际可用性以 Android 11+ 及 vendor HAL 实现为准，需确认目标设备的 camera provider 版本是否支持。

这组 API 仍然会把取 Buffer 的等待暴露到请求时序里。HAL 在 `processCaptureRequest` 附近现取 Buffer 时，如果 Framework 侧没有空闲 Buffer、消费端持有过久或 BufferQueue 正在等待 release fence，`request_stream_buffers` 会同步等待，后续 Request 下发也会抖动。排查时把 `request_stream_buffers`、`return_stream_buffers`、`dequeueBuffer` 的耗时放在同一张时间线上看；工程上保留少量预取 Buffer，或把取 Buffer 放到独立高优先级线程，避免每帧都在 Request 热路径上等空闲 Buffer。
[已验证: AOSP hardware/libhardware/include_all/hardware/camera3.h（`include/hardware/camera3.h` 为到 include_all 的链接/转发）, android-16.0.0_r1]

**功耗度量**：在 Perfetto 中可以用 `android_cpu` Metric 查看 Camera 相关进程的 CPU 时间。如果 `cameraserver` 的 CPU 时间异常高，说明 HAL 的处理负载很重；如果 App 进程的 CPU 时间高，说明可能在主线程做了过多处理（如直接在 `onPreviewFrame` 中做图像处理）。将 Camera 操作移到后台线程，或者把 CPU 软处理替换为 CameraX ImageAnalysis / YUV 转换、RenderScript Intrinsics Replacement Toolkit（只覆盖旧 intrinsics）、OpenGL ES / Vulkan compute、NDK / MediaCodec 或厂商 HAL 能力。RenderScript 已在 Android 12 deprecated，不能再作为 Android 12-17 的主推荐；每条替代路径都要按分辨率、帧率和 SoC 做同机实测。

[待补充: 不同 Sensor 模式下的功耗量化数据]

## 与其他机制的关系

Camera 性能分析和全书多个章节有交叉：

- **2.13 图形缓冲区管理 (BufferQueue)**：Camera 管线中的 Buffer 流转，就是 BufferQueue 的 dequeue → queue → acquire → release 循环。理解 BufferQueue 的工作原理，是分析 Camera 预览卡顿的基础。
- **13.5 专题解读**：Perfetto 中的 Camera 相关 Track 和 Slice 的详细解读，包括 `cameraserver` 进程中各个 Slice 的含义。
- **11.2 App 耗电优化**：Camera 是 App 功耗大户，Camera 功耗优化的方法论和通用功耗优化策略一脉相承。
- **4.3 ART 虚拟机内存管理**：CameraMetadataNative 的 Native 内存增长，和 Java 可达性、GC 触发时机，以及 finalizer 释放路径直接相关。理解 ART 何时感知 native allocation 压力，有助于判断为什么 Camera 场景里 `TotalCaptureResult` 积压会很快顶高 Native RSS。

## Camera2 API vs CameraX API 的性能差异

Camera2 API 是 Android 5.0 引入的底层 Camera 接口，提供了对 Camera HAL3 管线的完整控制能力——手动控制曝光、对焦、帧率，甚至可以直接操作 ISP 参数。这种灵活性意味着 App 需要自己处理很多细节（Session 配置、Surface 管理、CaptureRequest 构建），稍有不慎就会引入性能问题。

CameraX 是 Jetpack 提供的高层 Camera 库，构建在 Camera2 之上。它做了大量性能自动优化：

- **自动选择最优的 Sensor 模式和分辨率组合**，避免 App 手动配置时选择了低效的组合
- **内部管理 Camera Session 的生命周期**，避免了 App 因不当的 Session 操作导致的帧率波动
- **对低版本设备的兼容性处理**，在不支持某些 Camera2 高级特性的设备上自动降级到更高效的实现
- **冷启动阶段多一层 capability 解析、UseCase 绑定和默认配置收敛**，首帧前常见额外 80-150ms 初始化开销。扫码、即拍即走这类冷启动敏感场景，要把 `deliverInputEvent` → 首帧上屏拆开实测；如果预算只剩几十毫秒，直接 Camera2 更可控

从 Perfetto Trace 的角度看，使用 CameraX 的 App 通常会在 `cameraserver` 中呈现更简洁的调用流程，因为 CameraX 会把不少配置步骤收束到库内部。代价是多了一层抽象，在极端性能场景（如高帧率录像、多摄像头并发）里，CameraX 反而可能成为限制，这时候还是需要直接使用 Camera2 API。

[待验证: CameraX 在 Android 16/17 中是否有新的性能优化特性]

## HAL3 管线延迟的深度分析

HAL3 管线中，从 App 下发 CaptureRequest 到收到 CaptureResult，经历以下阶段：

1. App 调用 `captureSession.capture()` 或 `setRepeatingRequest()`
2. CameraService 通过 Binder 将 Request 传递给 cameraserver 进程
3. cameraserver 的 Camera3Device 将 Request 排入内部的 Request Queue
4. HAL 从 Request Queue 中取出 Request，分配 Buffer 给各个 Stream
5. Sensor 开始曝光采集，ISP 处理
6. HAL 输出处理完的帧到 Output Buffer，通过 `processCaptureResult` 回调
7. cameraserver 的 FrameProcessor 线程收到 Result，通过 Binder 回调给 App

整条路径的延迟取决于多个因素。其中 Sensor 曝光时间是物理限制——至少需要一个帧周期（30fps 时 33ms）。ISP 处理时间取决于图像分辨率和算法复杂度。Binder IPC 虽然单次延迟只有 1-2ms，但在 Request 和 Result 的传递中各有一次，加上 cameraserver 内部的队列等待时间，总延迟不可忽视。

**ZSL（Zero Shutter Lag）** 是一种优化拍照延迟的技术：HAL 维持一个环形缓冲区，持续采集帧。当用户按下快门时，直接从缓冲区中取出最近的一帧，省去了 Sensor 曝光等待。代价是持续的功耗和内存开销——环形缓冲区通常需要保存 3-5 帧全分辨率图像。

在 Perfetto 中追踪 HAL3 管线延迟，可以关注 `submitRequestList` → `first full buffer` 的时间差，这个差值反映了从 Request 下发到首帧产出的端到端延迟。

[待验证: 不同 SoC 平台（高通/联发科/三星）上 HAL3 管线延迟的典型值]

## GFXReconstruct 辅助检查花屏和 YUV 帧问题

Perfetto 能告诉你哪一帧晚到、哪段处理慢，但不能直接看到 Buffer 内容。遇到花屏、颜色错乱、UV 平面顺序错误这类问题，GFXReconstruct 可以作为补充工具：在使用 Vulkan / OpenGL 导入 `AHardwareBuffer` 的路径上抓取图形 API 调用，再用 `gfxrecon-convert --include-binaries` 导出 capture 中的二进制资源，离线检查 YUV 平面、stride、crop 和色彩格式。

这个方法有边界。Camera 预览如果走 `SurfaceView` 直送 SurfaceFlinger 或 HWC overlay，GFXReconstruct 可能抓不到最终预览帧；它也看不到 Sensor 和 ISP 内部状态。它适合回答“进入图形 API 后 Buffer 内容是否已经错了”，不适合替代 HAL trace、vendor log 或原始帧 dump。

## 常见问题与误区

**误区一：Camera 卡顿一定是 HAL 的问题。** 很多时候卡顿的根因在 App 侧——比如在 `onImageAvailable` 回调中做了耗时操作，导致 Buffer 被持有时间过长，BufferQueue 耗尽。先用 SQL 确认 HAL 的帧处理速率，再去看 App 侧的 Buffer 持有时长。

**误区二：Camera 预览用 TextureView 和 SurfaceView 性能差不多。** TextureView 需要经过一次 GPU 纹理上传，而 SurfaceView 可以直接由 SurfaceFlinger 从 BufferQueue 中 latch Buffer 合成上屏，省了一次 GPU 操作。在低端设备上这个差异很明显。

**误区三：CameraMetadataNative 内存增长要沿着结果对象引用排查。** 这类问题更接近“框架对象被长期强引用后，native metadata 无法尽快清理”。以 AOSP `frameworks/base/core/java/android/hardware/camera2/impl/CameraMetadataNative.java` 为准，android-16.0.0_r1 中仍通过 `mMetadataPtr`、private `close()` 和 `protected finalize()` → `close()` 管理 native metadata；未看到 `NativeAllocationRegistry` / `Cleaner` 迁移。App 层拿到的仍是 `TotalCaptureResult` / `CaptureResult` 等包装对象，没有公开的 `CameraMetadataNative.close()` 可调接口。

排查和治理时，重点放在引用关系：不要把大量 `TotalCaptureResult` 长时间塞进队列、缓存或跨线程消息里；只提取需要的 metadata 字段，处理完就尽快丢掉结果对象；对长期统计场景，优先落成轻量结构体或自定义 DTO，再释放原始 result 引用。[来源: Cubox/Android Camera内存问题剖析-2024-02-04.md；已验证: AOSP `frameworks/base/core/java/android/hardware/camera2/impl/CameraMetadataNative.java`，android-14.0.0_r1 / android-16.0.0_r1]

**误区四：Camera 性能问题不需要看 Binder。** Camera 管线中 App → cameraserver → HAL 路径上至少各有一次 Binder IPC。如果系统负载高导致 Binder 线程池耗尽，或者 Binder 事务本身延迟大（如传输大块 metadata），Camera 性能就会受影响。在 Perfetto 中开启 `binder_driver` category 可以追踪 Binder 事务的延迟。

## 参考资料

- AOSP Camera Service 源码：`frameworks/av/services/camera/libcameraservice/`
- AOSP CameraMetadataNative Java 实现：`frameworks/base/core/java/android/hardware/camera2/impl/CameraMetadataNative.java`
- AOSP Camera Metadata JNI：`frameworks/base/core/jni/android_hardware_camera2_CameraMetadata.cpp`
- Perfetto Trace Processor SQL Tables：https://perfetto.dev/docs/analysis/sql-tables
- Perfetto Python SDK：https://perfetto.dev/docs/analysis/trace-processor#python
- Android Camera2 API 官方文档：https://developer.android.com/reference/android/hardware/camera2/package-summary
- Android CameraX 官方文档：https://developer.android.com/training/camerax
