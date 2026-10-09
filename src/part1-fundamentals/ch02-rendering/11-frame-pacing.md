---
title: Frame Pacing Library 与帧节奏控制
chapter: '2.11'
section: '2.11'
status: finalized
applicable_versions: Android 4.4 (API 19, Swappy 当前 release minSdk) - Android 17 (API 37)；Java Choreographer 自 API 16 可用
last_verified: '2026-07-25'
last_verified_against: Android 17 / API 37 / android-17.0.0_r1；android17-6.18-2026-06_r6；AGDK frame-pacing release @ f81f888fe11e；Vulkan 1.4.335；Writer rendering_pipelines S01/S08/S12
confidence: high
sources:
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/vulkan/libvulkan/driver.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/vulkan/libvulkan/swapchain.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/vulkan/vkprofiles/profiles/VP_ANDROID_17_requirements.json
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/nativewindow/include/android/native_window.h
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp
- type: aosp
  path: https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/metrics/sql/android/android_frame_timeline_metric.sql
- type: library
  path: https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/f81f888fe11e9540dd580edf5993232172ed3cbe/games-frame-pacing/
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c
- type: specification
  path: https://github.com/KhronosGroup/Vulkan-Docs/blob/v1.4.335/proposals/VK_EXT_present_timing.adoc
- type: official
  path: https://developer.android.com/games/sdk/frame-pacing
- type: official
  path: https://developer.android.com/games/develop/vulkan/frame-pacing-extensions
- type: material
  path: S01_baseline_12_anchor_pipeline/source.md
- type: material
  path: rendering_pipelines/S08_native_graphics_type.md
- type: material
  path: rendering_pipelines/S12_video_overlay_hwc_type.md
tags:
- rendering
- frame-pacing
- swappy
- perfetto
- vulkan
related_chapters:
- '2.3'
- '2.9'
- '2.8'
- '2.2'
- '18.3'
---

# Frame Pacing Library 与帧节奏控制

平均 FPS 只回答一段时间内产出了多少帧，说不出每一帧在屏幕上停留了多久。游戏平均维持 60 FPS、显示屏工作在 90 Hz 时，如果提交时刻没有对齐显示周期，画面可能按 1、2、1、2 个刷新周期交替停留——计数器仍接近 60，运动却会发颤。

Frame pacing（帧节奏控制）要同时约束三件事：应用从哪个节拍开始生产、buffer 何时提交、这块 buffer 希望落在哪个显示周期。Android Frame Pacing Library，也就是 Swappy，把这组控制封装在 `SwappyGL_swap()` 和 `SwappyVk_queuePresent()` 里，借助 Choreographer 对齐节拍、用 presentation timestamp（期望上屏时间戳）选定目标周期、靠 fence 跟踪上一帧的完成情况，抑制 queue-stuffing。

> 源码基线：AOSP `android-17.0.0_r1`，内核 `android17-6.18-2026-06_r6`；Swappy 是随 APK 发布的 AGDK（Android Game Development Kit，Android 游戏开发套件）库，锚定 `frameworks/opt/gamesdk` 的 `android-games-sdk-games-frame-pacing-release` 分支提交 `f81f888fe11e`，排查线上应用时先记录实际打包的 Swappy 版本。

## 先分清四个控制量

动手调帧节奏之前，我们先把四个容易混在一起的控制量分开，它们各自回答不同的问题：

| 控制量 | 回答的问题 | 常见接口或证据 |
|---|---|---|
| render-loop tick（渲染循环节拍） | 何时采样输入、更新逻辑并开始一帧 | 引擎 scheduler（调度器）、`AChoreographer`、Java `Choreographer` |
| frame pacing（帧节奏控制） | 何时等待、何时提交，允许多少帧同时在途 | Swappy、自研 pacing、acquire/swap/present wait |
| presentation target（目标显示时刻） | 希望 buffer 对应哪个显示时刻 | `EGL_ANDROID_presentation_time`、`VK_GOOGLE_display_timing`、Android 17 的 `VK_EXT_present_timing` |
| frame-rate vote（帧率投票） | 内容倾向什么帧率，系统应如何选显示模式 | `ANativeWindow_setFrameRate()`、`Surface.setFrameRate()` |

这四项会互相影响，却谁也替代不了谁：Choreographer tick 只给出一帧工作的起点，frame-rate vote 只声明内容倾向的帧率，presentation target 只描述希望的时刻；队列深度、GPU 完成情况和显示反馈，仍要靠 pacing 算法一并处理。

## 帧节奏问题在 trace 中的表现

我们先看数字：90 Hz 的刷新周期约为 11.11 ms，而 60 FPS 内容的目标帧间隔约为 16.67 ms，两者没有整数倍关系。应用如果每次 GPU 工作一结束就 present，显示侧可能让相邻内容帧分别停留一个和两个刷新周期，重负载下间隔的组合还会更杂乱。

另一类情况是 queue-stuffing：应用持续以最快速度提交，BufferQueue 很快积累多个待显示 buffer。队列满后，渲染线程会在 acquire、swap 或 present 附近受到反压，看起来像是系统自动替应用“限帧”。这时输入已经在更早的逻辑帧采样，多出来的排队会直接增加触控到显示的延迟。

当然，trace 里很长的 wait slice 未必都要修：它可能是队列堵住后的被动阻塞，也可能是 pacing 主动施加的等待，后者的目的正是阻止队列继续变深。

诊断时，我们把下面几组信号放在一起比较：

- 目标 FPS、显示 refresh rate 与相邻 buffer 提交间隔是否相容。
- `SurfaceView` 轨道中的 buffered frames 是否长期大于 1，是否周期性顶满后再回落。
- acquire/swap/present 的阻塞是否与队列深度、release fence 或 GPU 完成时间同步出现。
- 输入采样到 buffer present 的延迟是否随 queue depth 增长。
- 支持 FrameTimeline 的窗口是否出现 `Buffer Stuffing`、`App Deadline Missed` 或 SurfaceFlinger 侧 jank。

单看平均 FPS、一次 `eglSwapBuffers()` 的耗时或一条 `vkQueuePresentKHR()` 的耗时，都无法单独定责：swap/present 里可能混着驱动积累命令后的 flush、等可用 slot、等 fence，也可能就是 pacing 的主动休眠。定责时我们要把 CPU、GPU、BufferQueue 和显示时间放进同一段 trace 对照。

## Swappy 的真实提交链

我们顺着源码看 Swappy 在一次 swap 前后到底做了什么。`f81f888fe11e` 的 OpenGL 路径由 `SwappyGL::swapInternal()` 组织，fence、presentation time、等待策略和统计分别位于 `SwappyGL.cpp`、`EGL.cpp` 与 `SwappyCommon.cpp`。

下面的伪代码节选只保留调用顺序，错误处理和成员访问已简化。

```cpp
// 伪代码，按 frameworks/opt/gamesdk android-games-sdk-games-frame-pacing-release 分支调用顺序整理
bool SwappyGL::swapInternal(EGLDisplay display, EGLSurface surface) {
    SwappyCommon::SwapHandlers handlers = {
        .lastFrameIsComplete = [&] { return lastFrameIsComplete(display); },
        .getPrevFrameGpuTime = [&] { return getEgl()->getFencePendingTime(); },
    };

    getEgl()->insertSyncFence(display);
    mCommonBase.onPreSwap(handlers);

    if (mCommonBase.needToSetPresentationTime()) {
        setPresentationTime(display, surface);
    }

    bool ok = (getEgl()->swapBuffers(display, surface) == EGL_TRUE);
    mCommonBase.onPostSwap(handlers);
    return ok;
}
```

从这段代码往下看：`insertSyncFence()` 在本次 swap 前插入 `EGL_SYNC_FENCE_KHR`，由内部的 waiter thread 异步观察完成状态；`lastFrameIsComplete()` 和 `getFencePendingTime()` 把上一帧的 GPU 进度反馈给 `SwappyCommon`。

决定等待的是 `onPreSwap()`：它综合 Choreographer 时序、上一帧完成情况和目标 swap duration，决定这一帧要不要等；pipeline mode 是否允许 CPU、GPU 流水并行，也会进入这个判断。`onPostSwap()` 记录本次提交并推进下一次目标时刻。`setPresentationTime()` 会先检查目标时间是否离下一次 VSync 太近——进入这个边界后，它直接跳过 `eglPresentationTimeANDROID()`，因为此时的目标已经失去意义。

所以 Swappy 的作用范围超过“替换一次 swap”：它用 fence 约束在途帧，用 presentation timestamp 选择显示周期，再依据观测到的 CPU/GPU 时间调整 swap interval 与 pipeline mode。

## Choreographer 与 DisplayManager 的回退路径

接入 Swappy 时，公开约定只有一条：`SwappyGL_init(JNIEnv*, jobject)` 与 `SwappyVk_initAndGetRefreshCycleDuration(JNIEnv*, jobject, ...)` 都必须接收 JNI env 和 Activity。内部 `ChoreographerThread` 的选择树是实现细节，源码中的 `vm == nullptr` 分支只描述内部对象如何选择节拍源，不能据此省掉公开入口要求的 Android 上下文。

我们直接看 `ChoreographerThread::createChoreographerThread()` 的选择顺序：

- `vm == nullptr`，或者 `sdkInt >= 24`，优先使用 `NDKChoreographerThread`。源码里 `NDKChoreographerThread::MIN_SDK_VERSION = 24`。
- `sdkInt < 24` 且 JVM、Activity 都在，尝试 `JavaChoreographerThread`。
- Java 路径初始化失败时，回退 `NoChoreographerThread`，日志会记录 `Using no Choreographer (Best Effort)`。
- `Type::App` 直接使用 `NoChoreographerThread`，表示调用方自行提供应用侧 Choreographer 节拍，并非完全不需要节拍源。

刷新率与显示模式的辅助路径同样有版本边界：`SwappyDisplayManager::MIN_SDK_VERSION` 是 28，`useSwappyDisplayManager()` 在 API 28—30 借助 Java helper 完成，但排除 API 30 preview SDK 1；API 31 起 NDK 自带 refresh-rate callback，Java helper 退出这条路径。

| 平台边界 | 公开接入前提 | 内部节拍来源 | 刷新率相关辅助 |
|---|---|---|---|
| API 19—23 | `SwappyGL_init()` 仍要求 JVM 和 Activity，公开主线是 OpenGL | Java Choreographer | 无 NDK Choreographer，Swappy 走 Java 回调 |
| API 24—27 | OpenGL 仍走 `SwappyGL_init()`；Vulkan 路径从这里开始成立 | NDK Choreographer 优先 | 无 `SwappyDisplayManager` |
| API 28—30 | 同上 | NDK Choreographer 优先 | `SwappyDisplayManager` 可维护支持的刷新周期与显示模式 |
| API 31+ | 同上 | NDK Choreographer + native refresh-rate callback | Java DisplayManager helper 退出主链 |

排查初始化故障时，API 19—23 先查 JNI/Activity 与 Java Choreographer，API 24+ 再检查 NDK Choreographer 符号、独立 ALooper 线程和 refresh-rate callback。`SwappyGL_isEnabled()` 也要纳入启动日志：系统属性或必需的 EGL extension 缺失会让 OpenGL 路径停用。

## Auto 模式与多刷新率按运行状态计算

Auto 模式常被理解成 90 FPS、45 FPS、30 FPS 三档阈值表。我们拿 `SwappyCommon::calculateSwapInterval(frameTime, refreshPeriod)` 的源码对照一下，就会对不上。它的逻辑是：

- `frameTime < refreshPeriod`，interval 取 1。
- 否则用 `frameTime / refreshPeriod` 做整数除法。
- 余数大于 `REFRESH_RATE_MARGIN = 500 ns` 时，再向上补 1。

```cpp
int SwappyCommon::calculateSwapInterval(nanoseconds frameTime,
                                        nanoseconds refreshPeriod) {
    if (frameTime < refreshPeriod) {
        return 1;
    }
    auto div_result = div(frameTime.count(), refreshPeriod.count());
    return div_result.quot +
           (div_result.rem > REFRESH_RATE_MARGIN.count() ? 1 : 0);
}
```

`interval` 是运行时算出来的刷新周期整数倍，库内没有 90 FPS、45 FPS、30 FPS 这样的固定档位表；官方文档列出的档位来自设备刷新率组合的示例，作参考即可。

多刷新率的选择同样在运行时完成。`setPreferredRefreshPeriod()` 遍历 `mSupportedRefreshPeriods`，寻找能容纳当前 frame time 的最短 swap duration；几段结果相近时，它会选较长的 refresh period，以降低显示刷新功耗。`ANativeWindow_setFrameRate()` 已加载且 window 已设置时，Swappy 直接提交 frame-rate vote，DisplayManager 路径只是回退。

源码里有几个常量，含义和三档阈值表是两回事：

- `mAutoSwapIntervalThreshold` 默认是 `50 ms`。观测到的帧时长超过该阈值后，auto swap interval 不再主动 sleep，让应用尽快追赶；这个阈值不是建议的目标帧预算。
- `REFRESH_RATE_MARGIN` 是 `500 ns`，只用于 interval 取整边界。
- `FrameDurations` 的采样窗口是 `2 s`，用来估计近期 CPU/GPU 的帧耗时。

拿 90 Hz 设备估算：22 ms 左右的 frame time 会被 `calculateSwapInterval()` 算成 2 个 refresh period，得到约 22.22 ms 的展示节奏。这个数来自运行时计算，不来自配置表里的“45 FPS 档位”。

## OpenGL、Vulkan 与非游戏场景的接入边界

我们先看 OpenGL 的接入骨架，重点在初始化顺序和每帧入口；实际项目还要处理失败、窗口重建和 `SwappyGL_destroy()`。

```cpp
bool swappyReady = SwappyGL_init(env, activity) && SwappyGL_isEnabled();
if (swappyReady) {
    SwappyGL_setWindow(window);  // 创建 EGLSurface 时使用的 ANativeWindow

    // 固定 60 FPS 示例；需要动态调节时保留默认 Auto 模式。
    SwappyGL_setAutoSwapInterval(false);
    SwappyGL_setAutoPipelineMode(false);
    SwappyGL_setSwapIntervalNS(16'666'666ULL);
}

while (running) {
    renderFrame();
    bool ok = swappyReady
        ? SwappyGL_swap(display, surface)
        : (eglSwapBuffers(display, surface) == EGL_TRUE);
    // ok == false 时用 eglGetError() 继续定位。
}
```

`SwappyGL_swap()` 接管提交时序；`SwappyGL_setWindow()` 的作用是让库能调用 `ANativeWindow_setFrameRate()`。window 缺失时 swap 仍可能成功，但库会记录 `ANativeWindow not configured, frame rate will not be reported to Android platform`——帧率不上报给平台，frame-rate vote 路径随之降级。另外，默认 Auto 模式会持续按观测值修改 interval，想固定目标就得先关掉 Auto。

统计接口位于 `swappyGL_extra.h`：启用 `SwappyGL_enableStats(true)` 后，在每帧 CPU 工作开始前调用 `SwappyGL_recordFrameStart()`，再用 `SwappyGL_getStats()` 读取直方图统计。`SwappyGL_init()` 返回成功只说明初始化通过，统计能力是否可用仍要看运行日志。

换到 Vulkan，顺序更关键：`vkCreateDevice()` 之前就要让 Swappy 检查可用的 device extensions，并把它返回的名称并入 `VkDeviceCreateInfo::ppEnabledExtensionNames`。下面的骨架省略两次枚举的容器分配和 Vulkan 对象创建，只展示顺序。

```cpp
// vkCreateDevice() 之前：把 requiredExtensions 合并进 enabled extensions。
SwappyVk_determineDeviceExtensions(physicalDevice,
                                   availableExtensionCount,
                                   availableExtensions,
                                   &requiredExtensionCount,
                                   requiredExtensions);

// 创建 VkDevice、VkQueue、VkSwapchainKHR 之后：
uint64_t refreshPeriodNs = 0;
if (!SwappyVk_initAndGetRefreshCycleDuration(
        env, activity, physicalDevice, device, swapchain, &refreshPeriodNs)) {
    // 记录失败并选择应用自己的 present 路径。
}

SwappyVk_setWindow(device, swapchain, window);
SwappyVk_setQueueFamilyIndex(device, queue, queueFamilyIndex);
SwappyVk_setAutoSwapInterval(false);  // 固定 interval；动态模式保留默认 true
SwappyVk_setAutoPipelineMode(false);
SwappyVk_setSwapIntervalNS(device, swapchain, refreshPeriodNs);

VkPresentInfoKHR presentInfo = { /* ... */ };
VkResult result = SwappyVk_queuePresent(queue, &presentInfo);
```

`SwappyVk_queuePresent(VkQueue, const VkPresentInfoKHR*)` 会代应用调用 `vkQueuePresentKHR()`，中间还可能改写 `pNext` 或插入同步命令。因此重建 swapchain 前应先调用 `SwappyVk_destroySwapchain()`，device 生命周期结束时再调用 `SwappyVk_destroyDevice()`；顺序反了，库内按 swapchain/device 保存的状态就会失效。

Unity、Unreal 这类引擎的集成方式与默认开关随版本变化，分析时我们记录引擎版本、graphics API、render pipeline 和 frame-pacing 配置；“引擎支持 Swappy”只是前提，某个 APK 是否启用，要看它的打包配置。

非游戏的 native 渲染器若只需要 VSync 驱动，直接用 `AChoreographer` 就够；Java 渲染循环则可以用 `Choreographer.FrameCallback`。下面的例子演示 callback 每次执行后把自己重新注册一次：

```java
Choreographer choreographer = Choreographer.getInstance();

Choreographer.FrameCallback callback = new Choreographer.FrameCallback() {
    @Override
    public void doFrame(long frameTimeNanos) {
        renderFrame(frameTimeNanos);
        choreographer.postFrameCallback(this);
    }
};

choreographer.postFrameCallback(callback);
```

这段代码只把 CPU 工作起点对齐到显示节拍，缺少 presentation timestamp、GPU 完成反馈和在途帧控制，起不到 Swappy 的完整作用；官方 Frame Pacing 文档也明确指出，单独使用 Choreographer 仍可能在长帧场景触发 buffer-stuffing，也就是前文所说的 queue-stuffing。

## Android 17 的 Vulkan present timing

Android 17/API 37 新增了 `VK_EXT_present_timing` 平台支持。对自研 Vulkan pacing 来说，这多了一套标准接口：我们可以查询 swapchain 支持的 time domain（时钟域），为 present 请求指定目标时间，并读取 `QUEUE_OPERATIONS_END`、`REQUEST_DEQUEUED`、`IMAGE_FIRST_PIXEL_OUT`、`IMAGE_FIRST_PIXEL_VISIBLE` 等 present 阶段的反馈。

在 `swapchain.cpp` 的映射里，前两项分别对应 render-complete timestamp 与 composition-latch timestamp；后两项目前都落在同一个 actual-present timestamp 上，两者之差也就给不出 scan-out（扫描输出）时长。该扩展与较早的 `VK_GOOGLE_display_timing` 解决相近问题，但接口更标准，反馈阶段也更细。

AOSP 的 `VP_ANDROID_17_requirements.json` 把 `VK_EXT_present_timing`、`VK_KHR_present_id2` 和 `VK_KHR_present_wait2` 列为 Android 17 Vulkan Profile 的 `MUST` 项。这个 Profile 约束的是 Android 17 首发设备和新芯片的能力；应用仍要做自己的运行时检查，升级设备、定制系统、驱动状态和 feature 开关都可能造成差异。

`android-17.0.0_r1` 的 Vulkan loader 公布这个扩展是有条件的，`EnumerateDeviceExtensionProperties()` 只有在以下三项都满足时才加入 `VK_EXT_present_timing`：

1. `service.sf.present_timestamp` 为 true；
2. `present_timing_ext` 平台 flag 已开启；
3. ICD（Installable Client Driver，可安装客户端驱动）支持该扩展硬依赖的 calibrated timestamps（校准时间戳）能力。

所以应用仍要自己执行 `vkEnumerateDeviceExtensionProperties()`，并通过 `VkPhysicalDevicePresentTimingFeaturesEXT`、`VkPhysicalDevicePresentId2FeaturesKHR` 等 feature 结构查询、启用所需能力；查询 past presentation timing 之前，还要先用 `vkSetSwapchainPresentTimingQueueSizeEXT()` 配置反馈队列。

Android 17 的实现目前只公布 absolute scheduling，还不支持 relative scheduling；`vkGetSwapchainTimeDomainPropertiesEXT()` 返回 `VK_TIME_DOMAIN_PRESENT_STAGE_LOCAL_EXT`。要与 CPU 时钟关联，按规范经 calibrated timestamp 机制转换即可，不要把接口时间域直接写死成 `CLOCK_MONOTONIC`。

`targetTime = 0` 时，Android Vulkan WSI（Window System Integration，窗口系统集成层）不会设置 requested-present timestamp；非零目标会传入 native window。`BufferQueueConsumer::acquireBuffer()` 只在目标位于合理的未来窗口时返回 `PRESENT_LATER`，表示当前还不到取得该 buffer 的时刻；目标若比本轮 `expectedPresent` 晚超过 1 秒，系统会按安全规则立即处理，免得异常时间戳长期占住队列。

到这里要把平台能力和库实现分开看：`f81f888fe11e` 的 `SwappyVk` 仍按 `VK_GOOGLE_display_timing` 是否可用，在 `SwappyVkGoogleDisplayTiming` 与 `SwappyVkFallback` 之间选择，这个提交还没有用上 `VK_EXT_present_timing`、`VK_KHR_present_id2` 或 `VK_KHR_present_wait2`。

- 使用 Swappy 时，按 APK 打包版本的源码和运行日志判断它选择了哪个实现。
- 自研 pacing 可以在 Android 17 设备上优先探测 `VK_EXT_present_timing`，再按能力回退。
- 设备枚举出新扩展，不表示现有 Swappy 会自动切换到新接口。

### Android 17 的 producer throttling 开关

Android 17/API 37 还新增了 `Surface.setProducerThrottlingEnabled()` 和对应的 `ANativeWindow_setProducerThrottlingEnabled()`，控制 producer throttling，也就是生产端在下游仍忙时主动放慢提交。Java API 带 `FLAG_BQ_PRODUCER_BACKPRESSURE_CONTROL` 标记，`BufferQueueProducer` 的分支受 `bq_producer_backpressure_control` 平台 flag 保护；设备行为与 API 37 文档不符时，要同时确认系统镜像的 flag 状态。

功能启用时默认值为 true：producer 在 consumer 仍处理上一块 buffer 时调用 `queueBuffer()`，CPU 可能在 `eglSwapBuffers()` 或 `vkQueuePresentKHR()` 附近等待上一帧 GPU 工作完成。

设置为 false 关闭的是 `queueBuffer()` 处的 CPU 限速。CPU 生产速度超过 GPU 时，队列容量仍会在后续 dequeue 或 `vkAcquireNextImageKHR()` 处形成自然反压；该 API 不会取消 BufferQueue 容量、fence 语义或应用自己的 in-flight frame（同时在途帧）上限。异步模式下该设置没有效果，throttling 始终启用。

这项能力适合已经用 semaphore、fence 和有限在途帧做好显式同步的 Vulkan 渲染器。旧应用若把 present 中的 stall 当作隐式同步，直接关闭可能暴露资源复用错误，或让 queue depth 增长。`f81f888fe11e` 的 Swappy release 实现早于该 API，也尚未调用它；接入 Swappy 的应用应先用 trace 确认当前 stall 来源，再决定是否由业务侧修改。

## 验证路径：SurfaceView、Perfetto、FrameStatistics 三条线一起看

验证前先把条件钉死：场景、目标 FPS、显示 refresh rate、分辨率、画质、温度和输入脚本都固定，再分别抓取 Swappy 开启与关闭时的 trace。两个样本若来自不同时间段，热降频、场景差异或刷新率切换都可能被误判成 pacing 收益。

### SurfaceView 与队列深度

AGDK 的 verify-improvement 页面仍给出下面的 `systrace.py` 命令，用于观察 `SurfaceView` channel 的 buffered-frame 计数。

```bash
python systrace.py -a your-app-package-name -o mygametrace.html \
  sched freq idle am wm gfx view sync binder_driver hal input aidl
```

启用 pacing 后，buffered-frame 计数应更稳定，长时间顶在较深队列的情况应减少。现代设备也可以用 Perfetto UI 录制相同类别，并同时开启 scheduler、frequency、graphics、view、input 和 GPU 数据源，诊断目标不变。

| 平台边界 | 优先观察项 | 说明 |
|---|---|---|
| API 19—30 | SurfaceView buffered frames、acquire/swap/present wait、GPU、SwappyStats | Android 12 前没有 FrameTimeline |
| API 31+ 普通窗口 | 上述信号加 `Expected Timeline`/`Actual Timeline` | FrameTimeline 可区分应用与 SurfaceFlinger 侧 jank |
| API 31+ `SurfaceView` 游戏 | SurfaceView channel、BufferQueue、GPU、fence、SwappyStats | Perfetto 官方 FrameTimeline 文档仍注明不支持 SurfaceView |

普通窗口的 FrameTimeline 查询结果，要和独立 `SurfaceView` layer 分开解释；SurfaceView 游戏优先看 BufferQueue、GPU、fence 和 Swappy 自身统计。

### FrameTimeline

FrameTimeline 要求 Android 12/API 31 及以上。`Expected Timeline` 是 scheduler 给这一帧的时间预算；`Actual Timeline` 从 `Choreographer#doFrame` 或 `AChoreographer_vsyncCallback` 开始，到 `max(GPU complete, buffer post)` 结束。读数时留意：后者的 `ts` 只标记这段实际时间线的起点，与物理屏幕的 present timestamp 是两回事，相邻 `actual.ts` 不能直接当作相邻上屏时间。

我们在 Perfetto UI 里按以下顺序展开：

- 应用进程的 Choreographer/AChoreographer callback 与 render-thread marker；
- `Expected Timeline` 和 `Actual Timeline`；
- GPU Render Stages 与 producer fence；
- 对应 layer 的 BufferQueue/SurfaceFlinger slice。

对于受 FrameTimeline 支持的窗口，下面的查询把预算、实际工作时长和 jank 归因放到同一行。它沿用 Android 17 Perfetto metric 中按 `upid + name` 关联 expected 与 actual slice 的方式；`upid` 是 Perfetto 为进程分配的唯一标识。

```sql
SELECT
  actual.name AS vsync_token,
  actual.layer_name,
  actual.ts / 1e6 AS ts_ms,
  actual.dur / 1e6 AS actual_dur_ms,
  expected.dur / 1e6 AS expected_dur_ms,
  actual.on_time_finish,
  actual.present_type,
  actual.jank_type
FROM actual_frame_timeline_slice actual
LEFT JOIN expected_frame_timeline_slice expected
  ON expected.upid = actual.upid
 AND expected.name = actual.name
WHERE actual.upid = (
  SELECT upid FROM process WHERE name = 'your.package.name' LIMIT 1
)
ORDER BY actual.ts DESC
LIMIT 20;
```

`on_time_finish = 0` 表示应用没有按预算完成；`present_type` 区分 early、on-time、late、dropped；`jank_type` 给出 `App Deadline Missed`、`Buffer Stuffing`、SurfaceFlinger scheduling 等分类。一个 vsync token 关联同一帧的各个阶段，可能落在多个 layer 上；分析时把 `layer_name` 一并保留，只按 token 聚合会丢掉这层信息。

### SwappyStats

Swappy 自身提供第三组证据。启用 `SwappyGL_enableStats(true)` 或 `SwappyVk_enableStats(swapchain, true)` 后，应用应在每帧 CPU 工作开始前调用对应的 `recordFrameStart()`；结果既可以通过 `SwappyGL_getStats()`/`SwappyVk_getStats()` 取得，也会用 `FrameStatistics` tag 输出到 logcat。

Vulkan 有一条额外限制：`SwappyVkFallback` 的 `enableStats()`、`recordFrameStart()` 与 `getStats()` 都只打印 unsupported，Vulkan 统计只在 `SwappyVkGoogleDisplayTiming` 实现下成立。所以“已经调用 enableStats”还不算数，要确认当前选择的是哪个实现。

`SwappyStats` 的四组直方图分别回答不同问题：

- `idleFrames`：渲染完成后，在合成器队列里又等了几个 refresh period；
- `lateFrames`：比目标 presentation time 晚了几个 refresh period；
- `offsetFromPreviousFrame`：相邻两帧之间隔了多少个 refresh period；
- `latencyFrames`：从 `recordFrameStart` 到实际 present 经过了多少个 refresh period。

下面列出 `FrameStatistics.cpp` 的固定 logcat 字段名，便于在采样日志中定位：

```text
I/FrameStatistics: == Frame statistics ==
I/FrameStatistics: total frames: <runtime value>
I/FrameStatistics: Buckets: [0] [1] [2] ... [N]
I/FrameStatistics: idle frames: <bucket histogram>
I/FrameStatistics: late frames: <bucket histogram>
I/FrameStatistics: offset from previous frame: <bucket histogram>
I/FrameStatistics: frame latency: <bucket histogram>
```

读数时：`idleFrames` 上升，通常是 buffer 在合成器队列里多等了刷新周期；`lateFrames` 上升，说明目标 presentation time 与完成时刻错位；`latencyFrames` 增大，说明从 CPU 工作开始到 present 的在途周期变多。我们把这些直方图与 queue depth、GPU fence 和输入延迟放在同一测试窗口内比较，才能判断主动等待是在维持稳定节拍，还是目标 interval 配置不当。

## 帧率投票、ARR 与版本边界

ARR（Adaptive Refresh Rate，自适应刷新率）允许显示刷新率随内容和系统状态变化。Swappy 的 `setPreferredRefreshPeriod()` 在 `ANativeWindow_setFrameRate()` 可用且 window 已设置时，提交 `ANATIVEWINDOW_FRAME_RATE_COMPATIBILITY_DEFAULT` 类型的 frame-rate vote，旧平台才回退到 `SwappyDisplayManager` 的 preferred display mode。这个 vote 表达的是内容希望采用的帧率；最终的显示刷新率，系统还要综合其他可见 layer、切换策略和硬件 mode 决定。

Pacing 决定每一帧落在哪个显示周期，frame-rate vote 帮助系统选择适合内容的 refresh rate，两件事要配合起来。只投票而不控制提交时刻，短帧和长帧仍可能交替；只控制提交却不声明内容率，120 Hz 屏幕也可能为 60 FPS 内容做不必要的刷新。

同一个 `ANativeWindow` 上，应用不要让 Swappy 和业务代码同时持续调用 `Surface.setFrameRate()` 与 `ANativeWindow_setFrameRate()`：它们更新的是同一 Surface 的当前 vote，后续写入会改变先前设置，容易造成 mode 选择与 pacing 目标来回变化。系统如何综合多个 layer 的 vote 见 §2.2。

| 平台版本 | 与帧节拍直接相关的变化 |
|---|---|
| Android 4.1/API 16 | Java `Choreographer` 可用于应用帧回调；当前所核 Swappy release 的 minSdk（最低支持 API）仍是 19 |
| Android 7.0/API 24 | NDK `AChoreographer` 可用，Swappy 内部优先选择 native 路径 |
| Android 9—11/API 28—30 | Swappy 的 Java `DisplayManager` helper 参与刷新率与 mode 信息维护 |
| Android 11/API 30 | `ANativeWindow_setFrameRate()` 提供 native frame-rate vote |
| Android 12/API 31 | FrameTimeline 成为现代窗口 jank 诊断基线；Swappy 不再需要 Java DisplayManager helper |
| Android 15/API 35 | 支持设备引入 Adaptive Refresh Rate，刷新率选择更依赖平台策略 |
| Android 17/API 37 | 平台增加 `VK_EXT_present_timing` 与 producer-throttling 控制；现有 Swappy release 实现仍需按自身版本确认底层扩展 |

常见误判可以按下表排除：

| 现象或做法 | 为什么证据不足 | 继续检查 |
|---|---|---|
| 用 `Thread.sleep()` 达到目标 FPS | sleep 不知道 VSync 相位、队列深度和 GPU 完成状态 | Choreographer、present target、fence、queue depth |
| Vulkan 使用 `VK_PRESENT_MODE_FIFO_KHR` | FIFO（先进先出）保证队列顺序与 VBlank（垂直消隐期）语义，不提供完整的 Android pacing 反馈 | display timing、present interval、在途帧 |
| `eglSwapBuffers()` 很长 | 其中可能包含主动 pacing、free-slot wait（等待空闲 slot）或 release-fence wait | 线程状态、BufferQueue、fence、GPU |
| 平均 FPS 达标 | 平均值会掩盖短帧/长帧交替和额外排队 | frame-time 序列、present 间隔、输入到显示延迟 |
| Android 17 设备必有可用的 `VK_EXT_present_timing` | 平台版本不能代替 Vulkan runtime capability（运行时能力）检查 | extension 枚举、feature query、loader/driver 日志 |

## 参考资料

- Android Developers：[Frame Pacing Library](https://developer.android.com/games/sdk/frame-pacing)、[OpenGL ES 集成](https://developer.android.com/games/sdk/frame-pacing/opengl)、[Vulkan 集成](https://developer.android.com/games/sdk/frame-pacing/vulkan) 与 [验证方法](https://developer.android.com/games/sdk/frame-pacing/opengl/verify-improvement)
- Android Developers：[Vulkan frame pacing extensions](https://developer.android.com/games/develop/vulkan/frame-pacing-extensions)、[`Surface` API](https://developer.android.com/reference/android/view/Surface) 与 [Choreographer API](https://developer.android.com/reference/android/view/Choreographer)
- AGDK `f81f888fe11e`：[`SwappyGL.cpp`](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/f81f888fe11e9540dd580edf5993232172ed3cbe/games-frame-pacing/opengl/SwappyGL.cpp)、[`SwappyCommon.cpp`](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/f81f888fe11e9540dd580edf5993232172ed3cbe/games-frame-pacing/common/SwappyCommon.cpp)、[`ChoreographerThread.cpp`](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/f81f888fe11e9540dd580edf5993232172ed3cbe/games-frame-pacing/common/ChoreographerThread.cpp) 与 [`SwappyVk.cpp`](https://android.googlesource.com/platform/frameworks/opt/gamesdk/+/f81f888fe11e9540dd580edf5993232172ed3cbe/games-frame-pacing/vulkan/SwappyVk.cpp)
- Android 17 AOSP：[`vulkan/libvulkan/driver.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/vulkan/libvulkan/driver.cpp)、[`vulkan/libvulkan/swapchain.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/vulkan/libvulkan/swapchain.cpp) 与 [`VP_ANDROID_17_requirements.json`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/vulkan/vkprofiles/profiles/VP_ANDROID_17_requirements.json)
- Khronos Vulkan 1.4.335：[`VK_EXT_present_timing` proposal](https://github.com/KhronosGroup/Vulkan-Docs/blob/v1.4.335/proposals/VK_EXT_present_timing.adoc)
- Android 17 BufferQueue 与 producer throttling：[`Surface.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/view/Surface.java)、[`native_window.h`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/nativewindow/include/android/native_window.h)、[`BufferQueueProducer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueProducer.cpp) 与 [`BufferQueueConsumer.cpp`](https://android.googlesource.com/platform/frameworks/native/+/android-17.0.0_r1/libs/gui/BufferQueueConsumer.cpp)
- Perfetto：[FrameTimeline 文档](https://perfetto.dev/docs/data-sources/frametimeline)、[`actual_frame_timeline_slice` schema](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/perfetto_sql/stdlib/prelude/after_eof/events.sql) 与 [`android_frame_timeline_metric.sql`](https://android.googlesource.com/platform/external/perfetto/+/android-17.0.0_r1/src/trace_processor/metrics/sql/android/android_frame_timeline_metric.sql)
- 内核 `android17-6.18-2026-06_r6`：[`sync_file.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/drivers/dma-buf/sync_file.c) 与 [`dma-fence.h`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/linux/dma-fence.h)
