---
title: "Media3 视频播放渲染管线性能实战"
chapter: "22.43"
status: finalized
applicable_versions: "Android 11 (API 30) - Android 17 (API 37)"
tags: [media3, exoplayer, videoplayback, mediacodec, rendering, performance]
related_chapters: ["22.42", "12.33", "25.17", "25.18"]
created_by: "task2a-knowledge-gap"
created_date: "2026-07-17"
gap_source: "AOSP结构/官方文档"
last_verified: "2026-07-23"
confidence: medium-high
sources:
  - "DeepResearch/2026-07-17-android17-media3-video-rendering-pipeline-sourcecode.md"
  - "DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md"
last_body_apply_at: "2026-07-20T07:15:21+08:00"
last_body_apply_run_id: "20260720-071521-dbc00327"
last_body_apply_source: "source-index:27 DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md"
task2b_state: fixed
task6_state: reviewed
task9_state: reviewed
pipeline_stage: finalized
reviewed_date: "2026-07-23"
reviewed_by: "hermes-aiw-review-finalize-apply"
last_review_finalize_at: "2026-07-23T11:05:47+08:00"
last_review_finalize_run_id: "20260723-110520-166cb21f"
review_finalize_note: "2026-07-23 review: 已移除 outline 形态内容，将未由材料证明的 Media3/HDR/厂商实现标题级断言降级为排查边界；同步收敛 setOutputSurface、BufferQueue asyncMode、ANGLE-Vulkan fence/shader 等结论的适用范围。"
---

# 22.43 Media3 视频播放渲染管线性能实战

## 章节定位与结论边界

本章讨论 Media3 / ExoPlayer 视频播放在 Android 11–17 上常见的渲染性能排查路径：应用层播放器把压缩码流交给 `MediaCodec`，decoder 输出到 `Surface` 后进入 BufferQueue，最终由 SurfaceFlinger / 显示链路合成；如果播放器还启用了 GL 视频特效，则 `SurfaceTexture`、EGL/GLES、ANGLE-Vulkan 与 shader 编译也会进入首帧和掉帧归因范围。

需要先划清证据边界：本章的强证据来自 AOSP `android-17.0.0_r1` 的 `MediaCodec`、BufferQueue、`Surface` 与 ANGLE 源码，以及两份 DeepResearch 报告；它们可以支撑系统侧机制和调试方法，但不能直接推出「所有 Media3 版本默认启用某个 codec adapter / Buffer 模型 / HDR 策略」。因此，下文把可验证的源码机制写成排查依据，把 Media3 版本差异、OEM codec 行为、HDR/Dolby Vision overlay 能力和厂商驱动差异明确列为需要现场验证的变量。

## 实战排查主线

1. **先确认播放器输出路径**：记录 Media3/ExoPlayer 版本、`PlayerView` 使用 `SurfaceView` 还是 `TextureView`、是否启用 `VideoFrameProcessor` / 自定义 GL effect、是否播放 HDR 或高帧率内容。
2. **拆分首帧耗时**：把首帧拆成 codec 创建与配置、首批输入/输出 buffer、Surface / BufferQueue 建连、GL/ANGLE shader cold compile、fence wait 五段，避免把所有卡顿都归因到 `MediaCodec`。
3. **区分 Java API 与 native producer 能力**：`releaseOutputBuffer(index, renderTimestampNs)`、`setOutputSurface()` 是应用可感知的 MediaCodec API；`Surface::setSwapInterval(0)`、BufferQueue `asyncMode`、ANGLE-Vulkan fence 导入属于 native / EGL producer 或系统内部路径，不能写成 `PlayerView` 的通用开关。
4. **用证据收敛优化项**：codec 复用、Surface 动态切换、三缓冲、shader 预热、frame dropping / async 提交都应作为实验变量逐项验证；DRM、profile/level、分辨率、Surface 切换、OEM codec 能力不满足时，不应无条件池化或复用 decoder。

<!-- AIW-源码调研-2026-07-17 -->
## AOSP android-17.0.0_r1 源码级补充

> 本节由每日源码调研（research-gaps 自选轮）反哺。源码锚点：android-17.0.0_r1。

### MediaCodec Java 层关键路径

**异步模式回调派发**（`frameworks/base/media/java/android/media/MediaCodec.java@android-17.0.0_r1`）：

- `mCallback` / `EventHandler`（line 1820-1850）注册 9 类回调常量，其中 `CB_INPUT_AVAILABLE=1` / `CB_OUTPUT_AVAILABLE=2` / `CB_OUTPUT_FORMAT_CHANGE=4` / `CB_LARGE_FRAME_OUTPUT_AVAILABLE=7` / `CB_METRICS_FLUSHED=8` / `CB_REQUIRED_RESOURCES_CHANGE=9` 是 Android 17 上视频播放高频事件。
- `mBufferMode`（line 2451）区分 `BUFFER_MODE_LEGACY`（ByteBuffer）与 `BUFFER_MODE_BLOCK`（Android 12+ Block Model / Frame 路径）。材料能支撑 AOSP `MediaCodec` 具备该模式分支，但不能直接推出所有 Media3/ExoPlayer `MediaCodecVideoRenderer` 默认都走 `BUFFER_MODE_BLOCK`；实际路径需结合所用 Media3 版本、`MediaCodecAdapter` 实现与 codec 能力确认。
- `releaseOutputBuffer(int, long renderTimestampNs)`（line 4363）：ExoPlayer 在 SurfaceView 渲染时调用此 API 指定 VSYNC 渲染时间；SurfaceView 端要求 timestamp 与 `System.nanoTime` 差距 ≤ 1 秒，否则 fallback 到「最早可行时间」不丢帧模式。
- `setOutputSurface(@NonNull Surface surface)`（line 2643）：动态切换 decoder 输出 Surface（API 24+），video effect pipeline 关键 API。

### MediaCodec native 双线程模型

**`mCodecLooper` 与 `ANDROID_PRIORITY_AUDIO`**（`frameworks/av/media/libstagefright/MediaCodec.cpp@android-17.0.0_r1:2671-2676`）：

```cpp
mCodecLooper = new ALooper;
mCodecLooper->setName("CodecLooper");
err = mCodecLooper->start(false, false, ANDROID_PRIORITY_AUDIO);
```

`mCodecLooper` 独立线程运行 OMX state machine，`mLooper` 处理 API 请求；两者解耦避免 codec 卡顿阻塞 `releaseOutputBuffer` 等 API 调用。

**BufferChannel 回调注册**（line 2689-2693）：

```cpp
mCodec->setCallback(
        std::unique_ptr<CodecBase::CodecCallback>(
                new CodecCallback(new AMessage(kWhatCodecNotify, this))));
mBufferChannel = mCodec->getBufferChannel();
mBufferChannel->setCallback(
        std::unique_ptr<CodecBase::BufferCallback>(
                new BufferCallback(new AMessage(kWhatCodecNotify, this))));
```

`BufferCallback::onOutputBufferAvailable`（line 1072-1080）通过 `kWhatDrainThisBuffer` 消息通知 MediaCodec 主 looper，由 Java 层 `EventHandler` 派发到 `Callback.onOutputBufferAvailable`。

### setSurface generation number 机制

**`MediaCodec::connectToSurface`**（line 7691-7745）：

```cpp
static uint32_t sSurfaceGeneration = 0;
*generation = (getpid() << 10) | (++sSurfaceGeneration & ((1 << 10) - 1));
surface->setGenerationNumber(*generation);
...
sp<SurfaceListener> listener =
        new OnBufferReleasedListener(*generation, mBufferChannel);
err = surfaceConnectWithListener(
        surface, listener, "connectToSurface(reconnect-with-listener)");
```

**Generation number = PID<<10 | counter**，避免 disconnect → reconnect 时 GPU 端 stale frames 错误 attach 到新连接。`OnBufferReleasedListener` 把 surface buffer release 回调桥接到 `mBufferChannel`，保证 codec 端 buffer 索引与 surface buffer 生命周期一致。对支持动态切换的 decoder 路径，`setOutputSurface` 可作为减少 codec restart、BufferQueue reset 与 buffer 重新分配成本的优化手段；具体收益需要按设备、codec 与 Media3 adapter 实测确认。

### BufferQueue asyncMode 链路

**`BufferQueueProducer::setAsyncMode`**（`frameworks/native/libs/gui/BufferQueueProducer.cpp@android-17.0.0_r1:274-313`）：

```cpp
if ((mCore->mMaxAcquiredBufferCount + mCore->mMaxDequeuedBufferCount +
        (async || mCore->mDequeueBufferCannotBlock ? 1 : 0)) >
        mCore->mMaxBufferCount) {
    return BAD_VALUE;
}
int delta = mCore->getMaxBufferCountLocked(async,
        mCore->mDequeueBufferCannotBlock, mCore->mMaxBufferCount)
        - mCore->getMaxBufferCountLocked();
mCore->adjustAvailableSlotsLocked(delta);
mCore->mAsyncMode = async;
```

sync → async 时 `delta=+1`，多预留 1 个 slot 用于异步积压；async → sync 时 `delta=-1`，`adjustAvailableSlotsLocked` 把 slot 从 free 移到 unused。

**Async mode 下 producer 提交的 buffer 标记为 `mIsDroppable=true`**（line 1108-1112）：

```cpp
if (mCore->mAsyncMode) {
    item.mIsDroppable = true;
}
```

SurfaceFlinger 在 consumer 不及时 acquire 时可以丢弃过期帧——典型场景：SurfaceView 三缓冲 + video decode 速率 > display 刷新率。

**EGL CPU throttling 联动**（line 1232）：

```cpp
enableEglCpuThrottling = mCore->mAsyncMode || mCore->mDequeueBufferCannotBlock;
```

async mode 下启用 EGL CPU 节流，防止 producer 抢光所有 buffer 导致 consumer 无法 acquire。

### Surface::setSwapInterval 触发 setAsyncMode

**`frameworks/native/libs/gui/Surface.cpp@android-17.0.0_r1:725-735`**：

```cpp
const bool wasSwapIntervalZero = mSwapIntervalZero;
mSwapIntervalZero = (interval == 0);
if (mSwapIntervalZero != wasSwapIntervalZero) {
    mGraphicBufferProducer->setAsyncMode(mSwapIntervalZero);
}
```

这是 native `Surface` / EGL producer 在 `swapInterval=0` 时切入 BufferQueue asyncMode 的源码依据；Java 层 `PlayerView`/`SurfaceView` 并没有一个等价、通用的公开 `setSwapInterval(0)` 开关，因此不能写成「ExoPlayer 推荐配置」。更稳妥的结论是：当播放器或特效链路的 native GL producer 以 interval 0 提交到 Surface 时，BufferQueue 会进入 asyncMode，过期帧可被标记为可丢弃：

- `interval=1`（默认）：sync mode，UI 渲染适合；
- `interval=0`：async mode，视频/游戏适合，producer 不阻塞、过期帧可丢。

**`Surface::setBufferCount(3)`**（line 2604-2621）→ `setMaxDequeuedBufferCount(3 - 1 = 2)`，保留 1 个 slot 给 consumer 端 deque/acquire，实现三缓冲。

### ACodec setSurfaceParameters 扩展接口

**`ACodec::BaseState::setSurfaceParameters`**（`frameworks/av/media/libstagefright/ACodec.cpp@android-17.0.0_r1:6564`）支持四类参数：

- `PARAMETER_KEY_OFFSET_TIME`：渲染时间偏移（直播录制、屏幕捕捉）；
- `skip-frames-before`：跳过 startTimeUs 之前帧（seek 优化）；
- `PARAMETER_KEY_SUSPEND`：暂停输入（直播暂停、隐私遮挡）；
- `stop-time-us`：encoder 停止时间（限时长录制）。

### 实战调优清单（基于源码结论）

1. **优先评估异步模式**：`MediaCodec.setCallback(...)` 可降低同步 dequeue/release 的阻塞风险；是否复用 codec 实例要服从 DRM、profile/level、分辨率与 Surface 切换边界，不能无条件池化。
2. **区分 Java 播放器 Surface 与 native GL producer**：`Surface::setSwapInterval(0)` 能解释 asyncMode 进入条件，但不是 `PlayerView` 的通用 Java 调优项；只有自有 native/GL 特效 producer 能控制 swap interval 时才可作为实验变量。
3. **动态 `setOutputSurface`**：视频特效 pipeline（先渲染到 offscreen GL Surface 处理滤镜，再切到屏上 Surface）可省去 codec restart。
4. **HDR 渲染谨慎启用 surface 侧丢帧策略**：若播放器/codec adapter 暴露 frame-dropping 配置，可把它作为 4K/HDR/60fps 的实验变量；本章材料只证明 BufferQueue asyncMode 会把 buffer 标记为 droppable，不能保证所有 HDR 播放路径都会自动规避 jank。
5. **三缓冲 / buffer 数量**：`setBufferCount(3)` 对应 producer 侧最多 dequeue 2 个 buffer、保留 1 个 slot 给 consumer；它常用于在延迟和帧率稳定性之间折中，但是否可由应用直接配置取决于具体 Surface / producer 路径。

### 联动章节

- §18.16 BufferQueue（producer/consumer 基础，本次调研补充 asyncMode / generation number 机制）
- §18.11 ANGLE / OpenGL ES over Vulkan（视频特效 GL pipeline）
- §2.31 DisplayModeController / RefreshRateSelector（视频帧率 vs 设备刷新率匹配）
- §22.42（前后章节，video surface state）
- §12.33（多媒体子章节）

参考报告：`DeepResearch/2026-07-17-android17-media3-video-rendering-pipeline-sourcecode.md`

<!-- /AIW-源码调研-2026-07-17 -->


<!-- AIW-Body-Apply-ANGLE-2026-07-20 -->
## ANGLE（GLES-over-Vulkan）对视频特效链路的影响

> 本节把 ANGLE / Vulkan 翻译层材料补入 §22.43 的 Media3 视频特效语境。边界：仅讨论 Android 17 / API 37（AOSP `android-17.0.0_r1`）中已由材料验证的路径，不扩展到 Android 18/API38+。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

### 选择机制：先确认播放器进程是否真的跑在 ANGLE 上

Media3 的 `VideoEffectProcessor`、`SurfaceTexture → GL_EXTERNAL → Fragment Shader` 这类链路通常以 OpenGL ES 作为应用侧入口；在启用 ANGLE 的设备上，GLES 调用会落到 ANGLE-Vulkan 后端，而不是直接进入厂商 GLES driver。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

Android 17 的 ANGLE 选择不是单一开关，而是 `GraphicsEnvironment.setupAngle()` 中的 **Settings choice → `persist.graphics.egl` → `ro.hardware.egl`** 三层优先级，再叠加 `Flags.useQueryAngleChoice()` 分支：当用户/系统决策为 NATIVE 且只读属性不是 `angle` 时，框架会调用 `nativeSetAngleInfo("", true, packageName, null)`，让 Loader 维持 system driver；DEFAULT 则先看 `persist.graphics.egl`，再退到 `ro.hardware.egl`。[已验证: GraphicsEnvironment.java android-17.0.0_r1 line 698-786; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

对播放器或短视频 App 的实践含义是：不要只凭设备型号或开发者选项判断「已经启用 ANGLE」。在定位滤镜首帧慢、VSync 抖动或 shader cold compile 时，先在同一进程内读取 `glGetIntegerv(GL_RENDERER)`；若返回字符串包含 `ANGLE`，再把后续 Perfetto / logcat 观测归入 ANGLE-Vulkan 路径，否则应按 native GLES / vendor driver 路径排查。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

### Loader 生命周期：切换 driver 不是运行时热切

`GraphicsEnv::setAngleInfo()` 在 native 层只接受一套 ANGLE 参数，并在重复设置时触发强约束；这意味着通过 Settings 或属性修改 ANGLE 选择后，播放器进程必须重启，不能假设正在播放的 Media3 实例会动态切到另一套 EGL/GLES 实现。[已验证: GraphicsEnv.cpp android-17.0.0_r1 line 599-619; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

`Loader::should_unload_system_driver()` 的真值表还给出一个调试边界：当 ANGLE namespace 已设置且不是 system ANGLE，或者处于 `shouldUseAngle() && !angleLoaded` 状态时，Loader 会卸载 system driver 后重试 ANGLE；但 `cnx->systemDriverUnloaded` 一旦为 true，后续不会再次卸载，避免循环。[已验证: Loader.cpp android-17.0.0_r1 line 160-225; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

因此，视频特效 A/B 实验应以「冷启动一次进程 = 一种 EGL/GLES backend」为单位采样；同一进程内反复切开关得到的首帧耗时、shader 编译耗时和掉帧统计都可能混入 Loader 状态，不适合作为 ANGLE 与 native GLES 的严谨对比。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

### APK fallback 与崩溃边界

`setupAngleFromApk()` 会把 `nativeLibraryDir:sourceDir!/lib/<abi>` 注入 ANGLE namespace，再尝试加载 `libEGL_angle.so`、`libGLESv1_CM_angle.so`、`libGLESv2_angle.so`；材料指出若 ANGLE APK 已安装但没有携带 native libs，Android 17 仍可能回退到 system partition 的 ANGLE/driver 路径，b/370113081 的 crash 风险边界并未被材料证明已收敛。[已验证: GraphicsEnvironment.java android-17.0.0_r1 line 825-839; Loader.cpp android-17.0.0_r1 line 632-660; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

播放器侧如果发现只有部分渠道包、ABI 或 OEM ROM 在开启视频滤镜后崩溃，应把 `libEGL_angle.so` / `libGLESv2_angle.so` 是否来自 APK、system ANGLE 还是 vendor GLES 作为第一组环境指纹记录，避免把 Loader fallback 问题误判为 Media3 `VideoFrameProcessor` 自身缺陷。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

### EGL native fence 到 Vulkan semaphore：同步等待的位置会变

在 ANGLE-Vulkan 后端，EGL native fence 不再只是 GLES driver 内部 fence。`SyncHelperNativeFence::serverWait()` 会 `dup(mFenceFd)`，把副本 fd 交给 `vkImportSemaphoreFdKHR`，并使用 `VK_SEMAPHORE_IMPORT_TEMPORARY_BIT_KHR` 与 `VK_EXTERNAL_SEMAPHORE_HANDLE_TYPE_SYNC_FD_BIT_KHR` 将 Android native fence 导入 Vulkan semaphore；原 primary fd 仍由 ANGLE 侧管理。[已验证: SyncVk.cpp android-17.0.0_r1 line 508-538; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

`SyncHelperNativeFence::clientWait()` 通过 `egl::Display::GetCurrentThreadUnlockedTailCall()` 把等待切到 GPU 线程语境执行，而不是简单阻塞 EGL 调用者；材料还指出 `SyncWaitFd()` 使用 `poll()` 并把小于 1ms 的正 timeout 强压到 1ms。[已验证: SyncVk.cpp android-17.0.0_r1 line 28-68, 587-630; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

这会影响视频特效链路的性能归因：如果 `SurfaceTexture` 更新、滤镜 FBO 合成或输出 Surface 交换附近出现 single-digit-ms 等待，不应只看 Java 层 `releaseOutputBuffer()` 或 Media3 render callback；还要在 Perfetto 中同时看 Vulkan submit/present、ANGLE GPU 线程和 fence wait 栈，否则容易把 ANGLE fence 导入成本误报成 MediaCodec 解码慢。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

### Shader 编译与 UBO 布局：滤镜冷启动的真实成本

ANGLE-Vulkan 的 shader 路径由 `CompilerVk::getTranslatorOutputType()` 返回 `SH_SPIRV_VULKAN_OUTPUT`，`CodeGen.cpp` 在 SPIR-V 输出类型下实例化 `TranslatorSPIRV`；`TranslatorSPIRV::translate()` 会经历 `translateImpl()`、DriverUniform 注入、SPIR-V id 分配和 `OutputSPIRV()` 序列化。[已验证: CompilerVk.cpp android-17.0.0_r1; CodeGen.cpp android-17.0.0_r1 line 72-78; TranslatorSPIRV.cpp android-17.0.0_r1 line 1158-1182; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

对 Media3 视频特效而言，这意味着「第一次启用滤镜卡顿」可能来自 GLSL → SPIR-V cold compile，而不是 MediaCodec 初始化或 BufferQueue 重分配；材料给出的优化方向是：在播放器冷启动或进入编辑页时预热默认 UI shader、首个滤镜 material 和常用合成 shader，让后续 PipelineCache / ShaderBlobCache 命中。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

`ProgramVk.cpp` 中的 Vulkan default block encoder 使用 `PackedSPIRVBlockEncoder`，材料指出 ANGLE-Vulkan 的默认块布局比 std140 更紧凑；跨 native GLES、ANGLE-Vulkan、原生 Vulkan 三端复用 uniform buffer 时，要确认 shader 侧 layout 与 app 侧写入偏移是否一致，避免把 sampler binding 或 uniform 数据错位误判为滤镜算法错误。[已验证: ProgramVk.cpp android-17.0.0_r1 line 43-78; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

### 排查清单：把 ANGLE 作为视频渲染变量显式入表

1. 启动播放器后记录 `GL_RENDERER`、`/proc/<pid>/maps` 中是否存在 `libEGL_angle`，并把结果与 Media3 版本、SurfaceView/TextureView、HDR 开关一起写入性能样本。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]
2. 做 ANGLE vs native GLES 对比时，每个分组都冷启动进程；不要在同一进程内修改 Settings 后继续复用已有 EGL context。[已验证: GraphicsEnv.cpp android-17.0.0_r1 line 599-619; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]
3. 首帧慢分解为 Codec 初始化、BufferQueue 建连、GL/ANGLE shader 编译、fence wait 四段；只有 GL renderer 含 ANGLE 时，才把 `SyncHelperNativeFence` 与 TranslatorSPIRV 路径纳入主因候选。[来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]
4. 对出现 b/370113081 类 fallback 风险的设备，记录 ANGLE APK native libs 是否齐全与 Loader 实际加载的 so 来源；没有证据时不要把 crash 结论上升为 Media3 框架 bug。[已验证: GraphicsEnvironment.java android-17.0.0_r1 line 825-839; 来源: DeepResearch/2026-07-17-android17-angle-vulkan-game-engine-pipeline.md]

<!-- /AIW-Body-Apply-ANGLE-2026-07-20 -->


## Review finalize notes（2026-07-23）

本轮复审已将本章推进到 `finalized`。依据是 ANGLE / MediaCodec 两份 DeepResearch 材料能够支撑系统侧机制，且 2026-07-23 已完成三类收敛：

1. 顶部 `outline` 曾是提纲形态，且含「Android 17 Media3 Renderer 架构变化」「Android 17 HDR_OOTF」等未在本章材料中展开证明的标题级断言；2026-07-23 复审已将其改写为章节定位、排查主线与证据边界。
2. 已补入的 AOSP 源码段落曾有把 native `Surface` / BufferQueue / ANGLE 机制直接写成 Media3/ExoPlayer 默认实践的风险；复审已修正 `BUFFER_MODE_BLOCK` 默认路径、`setSwapInterval(0)` 推荐项、codec 池化、HDR 自动丢帧、`setOutputSurface` 收益等可证伪表述。
3. 后续若继续扩写，应按「Media3 官方 API/ExoPlayer adapter 行为 → AOSP MediaCodec/BufferQueue 证据 → 性能实战建议」补充更细的版本矩阵；当前版本已把未验证项降级为排查变量，而不是主线结论。


## 延伸阅读

### Media3 视频播放渲染管线 — AOSP android-17.0.0_r1 全链路源码级拆解
- 来源：`/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/2026-07-17-android17-media3-video-rendering-pipeline-sourcecode.md`
- 类型：DeepResearch 调研结果
- 摘要：从 MediaCodec Java 层 EventHandler/Callback 异步分发到 native 层 ALooper 双线程模型（mLooper + mCodecLooper），详解 BufferQueue generation number 防 buffer 跨连接复用、BUFFER_MODE_BLOCK vs BUFFER_MODE_LEGACY 的边界、setOutputSurface 动态切换 consumer 机制，以及 native Surface / EGL producer 的 swap interval 与 BufferQueue asyncMode / droppable buffer 关系。形成 MediaCodec → BufferQueue → SurfaceFlinger 完整链路闭环。
- 注入时间：2026-07-18
- 价值：§22.43 曾仅有提纲，此调研提供了可直接引用的源码级 Media3/ExoPlayer 渲染管线深度分析
