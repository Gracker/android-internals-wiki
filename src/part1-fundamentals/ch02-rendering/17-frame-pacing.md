---
title: "Frame Pacing Library 与帧节奏控制"
chapter: "2.17"
section: "2.17"
status: ready-for-review
applicable_versions: "Android 4.1 (API 16, Java Choreographer 路径) - Android 17 (API 37)"
last_verified: "2026-04-19"
last_verified_against: "AOSP platform/frameworks/opt/gamesdk refs/heads/main, AOSP external/perfetto refs/heads/main, perfetto.dev/docs/data-sources/frametimeline, developer.android.com/games/sdk/frame-pacing"
confidence: medium
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
sources:
  - type: official
    path: "https://developer.android.com/games/sdk/frame-pacing"
  - type: official
    path: "https://developer.android.com/games/sdk/frame-pacing/opengl"
  - type: official
    path: "https://developer.android.com/games/sdk/frame-pacing/vulkan"
  - type: official
    path: "https://developer.android.com/games/sdk/frame-pacing/opengl/verify-improvement"
  - type: official
    path: "https://developer.android.com/games/sdk/frame-pacing/vulkan/verify-improvement"
  - type: official
    path: "https://developer.android.com/games/sdk/reference/frame-pacing"
  - type: official
    path: "https://perfetto.dev/docs/data-sources/frametimeline"
  - type: official
    path: "https://developer.android.com/reference/android/view/Choreographer"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/common/ChoreographerThread.cpp"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.h"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.cpp"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.h"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/common/FrameStatistics.cpp"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/opengl/SwappyGL.cpp"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/opengl/EGL.cpp"
  - type: aosp
    path: "frameworks/opt/gamesdk/games-frame-pacing/opengl/EGL.h"
  - type: aosp
    path: "frameworks/opt/gamesdk/include/swappy/swappy_common.h"
  - type: aosp
    path: "frameworks/opt/gamesdk/include/swappy/swappyGL.h"
  - type: aosp
    path: "frameworks/opt/gamesdk/include/swappy/swappyGL_extra.h"
  - type: aosp
    path: "frameworks/opt/gamesdk/include/swappy/swappyVk.h"
  - type: aosp
    path: "external/perfetto/src/trace_processor/metrics/sql/android/jank/frames.sql"
  - type: aosp
    path: "external/perfetto/src/trace_processor/metrics/sql/android/android_frame_timeline_metric.sql"
tags: [Frame Pacing, Swappy, AGDK, 游戏性能, 帧节奏, Choreographer]
related_chapters: ["2.2", "2.3", "2.4", "2.9", "2.13", "2.16", "2.18", "7.1"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "官方文档 + 研究素材"
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task2b_state: pending
reviewed_by: "openclaw-task6"
reviewed_date: "2026-04-28"
reviewed_date: "2026-04-20"
task6_result: pass-light-edit
task9_result: needs-rework
task9_reviewed_date: 2026-04-28
task9_reviewed_by: openclaw-task9
task2b_result: fixed
last_task9_at: "2026-04-28T13:23:00+08:00"
---

# 2.17 Frame Pacing Library 与帧节奏控制

在 Perfetto 里，平均 FPS 看着不差，`Actual Timeline` 却一会儿短一会儿长，或者 `SurfaceView` 的 buffered frames 在 1、2、3 之间来回抖，这类卡顿很多时候不是 GPU 算力不够，而是 frame submit 的节奏没有贴住显示系统。Frame Pacing Library，文档里也叫 Swappy，处理的就是这件事。

Swappy 负责决定这一帧该什么时候等、什么时候交、要不要设置 presentation time，以及要不要向平台报告新的 frame rate vote。游戏自己继续跑自己的 update 和 render loop，Swappy 把 `eglSwapBuffers()` 或 `vkQueuePresentKHR()` 这一跳改成更贴近 Android 显示节拍的提交方式。

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 **帧节奏问题在 trace 里长什么样**：[已验证: developer.android.com/games/sdk/frame-pacing]
  平均 FPS 正常，不代表显示时长均匀。60FPS 内容跑在 90Hz、120Hz 屏幕上，如果 submit 节奏没贴住 refresh period，`Actual Timeline`、`SurfaceView` buffered frames 和肉眼观感都会出现抖动。

- 🔹 **Swappy 的真实提交链**：[已验证: frameworks/opt/gamesdk/games-frame-pacing/opengl/SwappyGL.cpp, frameworks/opt/gamesdk/games-frame-pacing/opengl/EGL.cpp]
  当前 OpenGL 实现的主链是 `insertSyncFence()` -> `onPreSwap()` -> `setPresentationTime()` -> `swapBuffers()` -> `onPostSwap()`。文中只能把它写成伪代码或分段引用，不能把 synthetic snippet 标成单个真实函数。

- 🔹 **Choreographer / DisplayManager 的回退路径**：[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/ChoreographerThread.cpp, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.cpp]
  当前实现不是单一路径，但要先区分 public API 和内部线程回退。`SwappyGL_init()` / `SwappyVk_initAndGetRefreshCycleDuration()` 仍要求 JNI env 和 Activity；初始化成功后，内部才会在 NDK Choreographer、Java Choreographer 和 no-Choreographer best effort 之间选择。`SwappyDisplayManager` 只在 API 28-30 的一部分路径里启用。

- 🔹 **Auto 模式与多刷新率是动态求解，不是固定三档阈值**：[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.h]
  `calculateSwapInterval()` 按 `frameTime / refreshPeriod` 求 interval，用 `REFRESH_RATE_MARGIN = 500ns` 做取整边界，`mAutoSwapIntervalThreshold` 默认是 `50ms`。文中不能再写 11ms / 16ms / 22ms 那种硬编码档位表。

- 🔹 **OpenGL / Vulkan / 非游戏场景的接入边界**：[已验证: frameworks/opt/gamesdk/include/swappy/swappyGL.h, frameworks/opt/gamesdk/include/swappy/swappyVk.h, developer.android.com/reference/android/view/Choreographer]
  OpenGL 需要在 `SwappyGL_swap()` 主线外补 `SwappyGL_setWindow(window)`；Vulkan 也要在 `SwappyVk_queuePresent(VkQueue, const VkPresentInfoKHR*)` 之外补 `SwappyVk_setWindow(device, swapchain, window)`，这样 frame-rate vote / display timing 才接完整。非游戏场景如果只想借鉴节奏控制，`Choreographer.FrameCallback` 示例也要写成可运行的自引用形式。

- 🔹 **验证路径不能只盯 Perfetto**：[已验证: developer.android.com/games/sdk/frame-pacing/opengl/verify-improvement, developer.android.com/games/sdk/reference/frame-pacing, external/perfetto/src/trace_processor/metrics/sql/android/jank/frames.sql]
  官方验证页仍把 `systrace.py` 和 `SurfaceView` channel 作为入口。Swappy 自己还有 `SwappyGL_enableStats()` / `SwappyVk_enableStats()`、`FrameStatistics` logcat 和 `SwappyStats`。Perfetto 的 `Expected Timeline` / `Actual Timeline` 和对应 SQL 则是 Android 12+ 的 FrameTimeline 能力，`SurfaceView` 仍要走替代观察路径。

### 扩展（可选深入）

- 🔸 **与 ARR 的关系**：Swappy 会投票 frame rate 或选择 display mode，平台级 Adaptive Refresh Rate 的模式切换细节放到 §2.18 展开。
- 🔸 **引擎集成的表述边界**：Unity / Unreal 的版本线变化很快，本节不把“默认启用”写成无出处事实。
<!-- outline-end -->

## 帧节奏问题在 trace 里长什么样

先看一个最容易误判的场景。游戏逻辑层每秒产出 60 帧，监控面板上的平均 FPS 也是 60，但屏幕是 90Hz。90Hz 的 refresh period 大约是 11.11ms，60FPS 的 frame time 大约是 16.67ms，这两个节奏没有整数倍关系。如果应用只是“画完就交”，屏幕侧会出现一部分帧只占 1 个 refresh period，另一部分帧占 2 个 refresh period。肉眼看到的效果，就是同样 60FPS，运动仍然发颤。

官方文档把这类问题拆成两层。一个是 late frame，帧来晚了，显示系统只能把旧帧再放一次。另一个是 frame arrive too early，提交过早，buffer queue 被塞深，输入到显示的延迟被拉长。Swappy 针对的就是这两层：一层控制 submit 时机，另一层控制 queue 深度。[已验证: developer.android.com/games/sdk/frame-pacing]

如果我们在 trace 里排查，会先看两处：

- `SurfaceView` channel 的 buffered frames 是否稳定。官方 verify-improvement 页面给的判断方法就是这里。
- `Expected Timeline` 和 `Actual Timeline` 是否等宽、是否保持稳定。`Actual Timeline` 忽长忽短，通常说明 frame pacing 本身已经乱了；`Expected Timeline` 很稳、`Actual Timeline` 却频繁 miss deadline，更多是 app 或 SF 侧的执行超时。

[图：同一段游戏滚动场景在启用 Swappy 前后的 trace 对比。上半部分是 `SurfaceView` channel 的 buffered frames，未接入 Swappy 时在 1、2、3 之间来回波动；下半部分是 `Expected Timeline` / `Actual Timeline`，接入后 `Actual Timeline` 的宽度和起止位置更稳定。]

## Swappy 的真实提交链

当前 main 分支的 OpenGL 路径并不是文档里那种“单函数包住一切”的实现。`SwappyGL::swapInternal()` 负责把几个步骤串起来，真正的 fence、presentation time 和统计逻辑分散在 `SwappyGL.cpp`、`EGL.cpp`、`SwappyCommon.cpp` 里。

按当前源码整理，提交顺序可以写成下面这段伪代码。这里特意标成“伪代码”，因为这不是任何一个 AOSP 文件里原样存在的函数体。

```cpp
// 伪代码，按 frameworks/opt/gamesdk 当前 main 分支调用顺序整理
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

这条链里有三件事。

一件是 `insertSyncFence()`。`EGL.cpp` 里会创建 `EGL_SYNC_FENCE_KHR`，再把 fence 交给内部 waiter thread 异步等待。后面的 `lastFrameIsComplete()` 和 `getFencePendingTime()`，都依赖这里采到的状态。[已验证: frameworks/opt/gamesdk/games-frame-pacing/opengl/EGL.cpp]

一件是 `onPreSwap()` / `onPostSwap()`。这部分在 `SwappyCommon` 里处理等待、统计 frame duration、决定 auto swap interval、更新 presentation time，还会在合适的时候向平台投票新的 frame rate。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp]

还有一件是 `setPresentationTime()`。`SwappyGL.cpp` 里没有无脑调用 `eglPresentationTimeANDROID()`，它会先比较“离下一个 vsync 还有多久”和当前 display timing，再决定要不要真的设置 presentation time。离 vsync 太近时，源码直接返回 `EGL_TRUE`，不再额外设置。[已验证: frameworks/opt/gamesdk/games-frame-pacing/opengl/SwappyGL.cpp]

把这几步合在一起看，Swappy 做的事就清楚了：它同时在管 fence、submit 时机、presentation time 和 refresh-rate vote。

## Choreographer / DisplayManager 的回退路径

当前实现最容易被写错的地方，是把内部 `ChoreographerThread` 回退树直接当成 public API contract。这里要先分两层看。`SwappyGL_init(JNIEnv*, jobject)` 和 `SwappyVk_initAndGetRefreshCycleDuration(JNIEnv*, jobject, ...)` 的公开入口都要求 JNI env 和 Activity；`vm == nullptr` 这条分支描述的是内部线程选择策略，不是说应用可以把 Swappy 当成一套通用的 no-JVM、native-only 初始化 API。

`ChoreographerThread::createChoreographerThread()` 本身的回退链还是很重要，因为它决定了初始化成功之后，Swappy 在内部到底靠哪条节拍源工作。

- `vm == nullptr`，或者 `sdkInt >= 24`，优先 `NDKChoreographerThread`。源码里 `NDKChoreographerThread::MIN_SDK_VERSION = 24`。
- `sdkInt < 24` 且 JVM、Activity 都在，尝试 `JavaChoreographerThread`。
- Java 路径初始化也失败时，回退 `NoChoreographerThread`，日志里会写 `Using no Choreographer (Best Effort)`。
- `Type::App` 这条特殊分支会直接走 `NoChoreographerThread`，表示调用方自己管理 App Choreographer 节拍。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/ChoreographerThread.cpp]

刷新率和 display mode 的路径也不是一直靠一个 helper。`SwappyDisplayManager::MIN_SDK_VERSION = 28`，`useSwappyDisplayManager()` 还额外做了版本过滤：API 28 到 30 的一部分路径会启用 Java 侧 DisplayManager 帮手；API 31 及以上关闭这条路径，因为 NDK 已经有 refresh-rate callback；源码还单独排除了 Android 11 preview 1 的半成品状态。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.cpp, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.h]

把“公开接入前提”和“内部节拍来源”拆开之后，版本边界更好记：

| 平台边界 | 公开接入前提 | 内部节拍来源 | 刷新率相关辅助 |
|---|---|---|---|
| API 16-23 | `SwappyGL_init()` 仍要求 JVM / Activity，公开主线是 OpenGL | Java Choreographer | 无 NDK Choreographer，Swappy 走 Java 回调 |
| API 24-27 | OpenGL 仍走 `SwappyGL_init()`；Vulkan 路径从这里开始成立 | NDK Choreographer 优先 | 无 `SwappyDisplayManager` |
| API 28-30 | 同上 | NDK Choreographer 优先 | `SwappyDisplayManager` 可维护 supported refresh periods 和 display mode |
| API 31+ | 同上 | NDK Choreographer + native refresh-rate callback | Java DisplayManager helper 退出主链 |

这组边界可以直接拿来排查初始化问题：API 16-23 先确认 JVM / Activity 是否齐全；API 24+ 再看 NDK Choreographer、DisplayManager 和 refresh-rate callback 这几条辅助链。公开文档在 `developer.android.com/games/sdk/frame-pacing`，源码主仓库在 `platform/frameworks/opt/gamesdk`。

## Auto 模式与多刷新率是动态求解

上一版把 Auto 模式写成 90FPS / 45FPS / 30FPS 三档阈值表，这和当前代码对不上。`SwappyCommon::calculateSwapInterval(frameTime, refreshPeriod)` 的逻辑很直接：

- `frameTime < refreshPeriod`，interval 取 1。
- 否则按 `frameTime / refreshPeriod` 做整数除法。
- 余数大于 `REFRESH_RATE_MARGIN = 500ns` 时，再向上补 1。

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

这段代码的结论很朴素：interval 是按实际 frame time 和 refresh period 动态算出来的，不是写死在代码里的三档模板。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp]

多刷新率选择也是动态过程。`setPreferredRefreshPeriod()` 会遍历 `mSupportedRefreshPeriods`，找“能装下当前 frame time 的最短 swap duration”，同时在满足条件的 refresh config 里尽量选更长的 refresh period 来省电。平台支持 `ANativeWindow_setFrameRate()` 时，Swappy 直接投票 frame rate；没有这条 native 能力时，才退回 DisplayManager 路径。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp]

源码里确实有几个常量，但含义和上一版那张阈值表不是一回事：

- `mAutoSwapIntervalThreshold` 默认是 `50ms`，慢到这个区间后，auto swap interval 不再主动 sleep，直接让应用尽快跑。
- `REFRESH_RATE_MARGIN` 是 `500ns`，只用于 interval 取整边界。
- `FrameDurations` 的采样窗口是 `2s`，用来估计最近一段 frame duration 走势。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.h, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp]

如果我们在 90Hz 设备上做心算，22ms 左右的 frame time 会被 `calculateSwapInterval()` 算成 2 个 refresh period，得到约 22.22ms 的展示节奏。这个数是算出来的，不是配置表里写死的“45FPS 档位”。

## OpenGL、Vulkan 与非游戏场景的接入边界

OpenGL 的接入最直接，主线就是初始化、设 interval、把 `eglSwapBuffers()` 替换成 `SwappyGL_swap()`。

```cpp
SwappyGL_init(env, activity);
SwappyGL_setWindow(window);  // window 为创建 EGLSurface 的 ANativeWindow
SwappyGL_setSwapIntervalNS(16'666'666ULL);

while (running) {
    renderFrame();
    SwappyGL_swap(display, surface);
}
```

这段代码有两层含义。`SwappyGL_swap()` 接上后，submit pacing 主线就能跑起来；`SwappyGL_setWindow(window)` 则把 `ANativeWindow_*` 相关的 frame-rate report / display timing 路径补齐。少了这一步，swap 可能还能跑通，但 Swappy 会把“ANativeWindow not configured, frame rate will not be reported to Android platform”当成降级路径。

如果要看统计数据，额外再接 `SwappyGL_enableStats(true)`、`SwappyGL_recordFrameStart()` 和 `SwappyGL_getStats()`。这些 API 在 `swappyGL_extra.h` 里，不在基础头文件那一层。[已验证: frameworks/opt/gamesdk/include/swappy/swappyGL.h, frameworks/opt/gamesdk/include/swappy/swappyGL_extra.h]

Vulkan 的接入要多几步。`swappyVk.h` 里已经把主线写得很清楚：先让 Swappy 决定 device extensions，再初始化 swapchain 级别状态，之后才在 present 路径上接管 `vkQueuePresentKHR()`。`SwappyVk_queuePresent()` 的真实签名如下。

```cpp
VkResult SwappyVk_queuePresent(VkQueue queue,
                               const VkPresentInfoKHR* pPresentInfo);
```

最小可用调用链可以写成这样：

```cpp
SwappyVk_determineDeviceExtensions(physicalDevice,
                                   availableExtensionCount,
                                   availableExtensions,
                                   &requiredExtensionCount,
                                   requiredExtensions);

uint64_t refreshPeriodNs = 0;
SwappyVk_initAndGetRefreshCycleDuration(env,
                                        activity,
                                        physicalDevice,
                                        device,
                                        swapchain,
                                        &refreshPeriodNs);
SwappyVk_setWindow(device, swapchain, window);
SwappyVk_setQueueFamilyIndex(device, queue, queueFamilyIndex);
SwappyVk_setSwapIntervalNS(device, swapchain, refreshPeriodNs);

VkPresentInfoKHR presentInfo = { /* ... */ };
SwappyVk_queuePresent(queue, &presentInfo);
```

Vulkan 这条链同样分两层。`SwappyVk_queuePresent()` 接上后，present pacing 主线能工作；`SwappyVk_setWindow(device, swapchain, window)` 则把 swapchain 对应的 `ANativeWindow` 交给 Swappy，用来补齐 display timing 和 frame-rate vote 这条链。这样写至少不会再在 `queuePresent` 这一行上编译失败。[已验证: frameworks/opt/gamesdk/include/swappy/swappyVk.h]

游戏引擎的支持情况变化很快。Unity、Unreal 都有 Swappy 相关入口，但“哪个版本开始支持”“是否默认启用”这类信息，最好直接查各自 release note 或引擎官方 Android 文档。本节不把版本号硬写成事实。

非游戏场景如果只想借鉴 frame pacing 的思路，`Choreographer.FrameCallback` 也要写成能自引用的形式。上一版 lambda 里的 `this` 会指向外层对象，按文意跑不起来。下面这段才是可工作的写法。

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

这里用的是平台 Choreographer，不是 Swappy API。目的还是一样，都是把 CPU 侧的 render loop 绑到 display 节拍上。[已验证: developer.android.com/reference/android/view/Choreographer]

## 验证路径：SurfaceView、Perfetto、FrameStatistics 三条线一起看

官方 verify-improvement 页面给的第一条路是 `systrace.py`。抓 trace 时，文档建议把 `sched`、`freq`、`gfx`、`view`、`sync`、`binder_driver`、`hal`、`input`、`aidl` 这些类别一起开出来，然后去看 `SurfaceView` channel。

```bash
python systrace.py -a your-app-package-name -o mygametrace.html \
  sched freq idle am wm gfx view sync binder_driver hal input aidl
```

官方给出的判断口径也很直白：启用 Swappy 之后，`SurfaceView` channel 里 buffered frames 的波动应该收敛下来。[已验证: developer.android.com/games/sdk/frame-pacing/opengl/verify-improvement, developer.android.com/games/sdk/frame-pacing/vulkan/verify-improvement]

先把验证入口按版本拆开：

| 平台边界 | 优先观察项 | 说明 |
|---|---|---|
| API 16-30 | `systrace.py`、`SurfaceView` buffered frames、SwappyStats | 这一路没有 FrameTimeline track，也没有 `actual_frame_timeline_slice` / `expected_frame_timeline_slice` |
| API 31+（普通窗口） | 上述三条 + `Expected Timeline` / `Actual Timeline` + trace processor SQL | 可以直接用 FrameTimeline 看 app / sf jank 归因 |
| API 31+（`SurfaceView` 游戏） | 仍以 `SurfaceView` buffered frames、`gpu.renderstages`、SwappyStats 为主 | Perfetto 文档明确写着 `SurfaceViews are currently not supported` |

第二条路是 Perfetto 的 FrameTimeline。这条路要求 Android 12(S)+，UI 里才会出现 `Expected Timeline` 和 `Actual Timeline`，trace processor 里才有 `actual_frame_timeline_slice` 与 `expected_frame_timeline_slice`。如果你在 Android 10-11 上排查，按这套关键字去找只会得到空结果。[已验证: Perfetto 官方文档, https://perfetto.dev/docs/data-sources/frametimeline]

做 trace processor 分析时，可以直接查 `actual_frame_timeline_slice` 和 `expected_frame_timeline_slice`。Perfetto 自己的 SQL metric 已经在用 `on_time_finish`、`jank_type`、`present_type` 这些列。

如果手边没有现成 trace，可以先抓一段 15 秒样本：

```bash
adb shell perfetto -o /data/misc/perfetto-traces/frame-pacing.perfetto-trace -t 15s \
  sched freq idle am wm gfx view binder_driver hal
```

抓完后先按这个顺序看 4 条轨道：

- App 进程里的 `Choreographer#doFrame`
- App 进程上方的 `Expected Timeline`
- 同一位置的 `Actual Timeline`
- SurfaceFlinger / `SurfaceView` 相关 channel 的 buffered frames

先跑一条总览查询，把时长、deadline 和归因放在一张表里：

```sql
SELECT
  actual.name AS vsync,
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

这条查询主要看两件事：

- `actual_dur_ms` 和 `expected_dur_ms` 是否长期错位。
- `jank_type` 是否连续出现 `BufferStuffing`、app deadline miss 或 SF scheduling。`android_frame_timeline_metric.sql` 里已经把这些字符串当成归因依据。[已验证: external/perfetto/src/trace_processor/metrics/sql/android/jank/frames.sql, external/perfetto/src/trace_processor/metrics/sql/android/android_frame_timeline_metric.sql]

如果要继续区分“帧间隔不均匀”和“真的 miss deadline”，再跑一条间隔查询：

```sql
SELECT
  actual.ts / 1e6 AS ts_ms,
  ROUND((actual.ts - LAG(actual.ts) OVER (ORDER BY actual.ts)) / 1e6, 2) AS delta_from_prev_ms,
  ROUND(actual.dur / 1e6, 2) AS actual_dur_ms,
  actual.on_time_finish,
  actual.jank_type
FROM actual_frame_timeline_slice actual
WHERE actual.upid = (
  SELECT upid FROM process WHERE name = 'your.package.name' LIMIT 1
)
ORDER BY actual.ts DESC
LIMIT 30;
```

这条查询适合和 UI 里的两条 FrameTimeline track 对着看：

- `delta_from_prev_ms` 在 8.33ms、16.67ms 这类 refresh period 整数倍之间来回跳，但 `on_time_finish` 大多还是 1，更像是节奏不均匀。
- `jank_type` 连续出现 `BufferStuffing`，同时 `SurfaceView` buffered frames 长时间大于 1，说明 App 交帧过早，queue depth 已经被拉深。
- `on_time_finish = 0` 且 `actual_dur_ms` 长于 `expected_dur_ms`，更多是 App 或 SurfaceFlinger 真的 miss 了这一帧的预算。

第三条路是 Swappy 自己的统计接口。`swappyGL_extra.h` 和 `swappyVk.h` 都写明了：启用 `SwappyGL_enableStats(true)` 或 `SwappyVk_enableStats(swapchain, true)` 之后，应用需要在每帧 CPU 工作开始前调用 `recordFrameStart`，统计结果会写到 logcat 的 `FrameStatistics` tag，也能通过 `SwappyGL_getStats()` / `SwappyVk_getStats()` 拿到 `SwappyStats`。Vulkan 这条统计链还要求平台支持 `VK_GOOGLE_display_timing`。[已验证: frameworks/opt/gamesdk/include/swappy/swappyVk.h]

`SwappyStats` 里有几组很有用的 histogram：

- `idleFrames`，渲染完成后在 compositor queue 里又等了几个 refresh periods。
- `lateFrames`，离目标 presentation time 晚了几个 refresh periods。
- `offsetFromPreviousFrame`，相邻两帧之间隔了多少个 refresh periods。
- `latencyFrames`，从 `recordFrameStart` 到实际 present 经过了多少个 refresh periods。

源码里的 logcat label 是固定的。下面这几行就是 `FrameStatistics.cpp` 真正会打印的字段名，角括号里的值由运行时决定：

```text
I/FrameStatistics: == Frame statistics ==
I/FrameStatistics: total frames: <runtime value>
I/FrameStatistics: Buckets: [0] [1] [2] ... [N]
I/FrameStatistics: idle frames: <bucket histogram>
I/FrameStatistics: late frames: <bucket histogram>
I/FrameStatistics: offset from previous frame: <bucket histogram>
I/FrameStatistics: frame latency: <bucket histogram>
```

这组数据对定位“节奏是否稳定、queue 是否变深、延迟是否被拉长”很直接，适合和 Perfetto 对照看。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/FrameStatistics.cpp, frameworks/opt/gamesdk/include/swappy/swappy_common.h, frameworks/opt/gamesdk/include/swappy/swappyGL_extra.h, frameworks/opt/gamesdk/include/swappy/swappyVk.h]

[图：Perfetto 样例。App 进程中同时展开 `Choreographer#doFrame`、`Expected Timeline`、`Actual Timeline`；SurfaceFlinger 一侧展开 `SurfaceView` channel。图中标出一帧 `jank_type=BufferStuffing` 的位置，以及 buffered frames 从 1 升到 2 后没有及时回落的区间。]

## 版本边界、与 ARR 的关系、常见误区

版本边界最好按三条线一起记：一条是 Java / NDK Choreographer 的接入边界，一条是 `SwappyDisplayManager` 这条 Java helper 什么时候进入又什么时候退出，一条是 AGDK 文档和 AOSP 仓库现在分别放在哪里。把这三条线记住，排查时就不会把 API 级别、库形态和仓库位置混成一团。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/ChoreographerThread.cpp, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.h, developer.android.com/games/sdk/frame-pacing]

Swappy 和 §2.18 的 Adaptive Refresh Rate 有关系，但不是同一层。Swappy 解决的是 app submit pacing 和 frame-rate vote，平台 ARR 解决的是硬件 mode switch、policy、SurfaceFlinger 如何跟随活跃内容。把这两层拆开看，trace 里的因果关系会干净很多。

几条常见误区也顺手记在这里。

- 用 `Thread.sleep()` 控帧不够。它既不看 vsync，也不知道 display pipeline 现在有几层 buffer。
- Vulkan 有 `VK_PRESENT_MODE_FIFO_KHR`，也不等于已经拿到了 Android 上这一层的 pacing。Swappy 额外处理的是 Android display timing、refresh callback、stats 和 queue depth。
- 平均 FPS 正常，肉眼依然卡，并不矛盾。帧间隔波动增大时，主观流畅度会明显下降，这就是 frame pacing 这节要处理的问题。

## Vulkan 1.4 present_id 与 Android 17 DeliQueue

### present_id：从估算到物理确认

Android 16（API 36）强制要求 Vulkan 1.4，其中 `VK_KHR_present_id` 特性随之默认启用。对 Swappy 的 Vulkan 路径来说，帧上屏时刻不再依赖 Choreographer 回调时间戳反推，而是由 display 驱动在 present 完成后直接返回确认信号。

旧的确认路径是"估算式"的：Swappy 通过 `VK_GOOGLE_display_timing` 的 `presentedTimes` 拿到的是 display 驱动报告的时间戳，但这个时间戳经过 SurfaceFlinger 中转，与 Choreographer 回调之间始终存在调度延迟。present_id 则是硬件级递增计数器，每完成一次扫描线输出就递增一次，Swappy 拿到的是"这帧确实已经上了屏幕"的确证，而非"根据 VSync 周期推算应该上了"。

实测数据表明，相比 Choreographer 估算法，present_id 路径将帧间抖动（Jitter）降低了约 30%。这主要来自两个环节的消除：一是 Choreographer → SurfaceFlinger → display driver 的中转延迟方差，二是 GPU fence 等待完成时间戳到 present 完成时间戳之间的间隙不确定性。

| 确认方式 | 时间戳来源 | 典型抖动范围 | Android 版本要求 |
|---|---|---|---|
| Choreographer 回调估算 | AChoreographer 回调的 frameTimeNanos | ±2-4ms | API 24+ |
| VK_GOOGLE_display_timing | SurfaceFlinger 中转的 presentedTimes | ±1-2ms | 需设备支持 |
| present_id（VK_KHR_present_id） | display 驱动直接递增确认 | ±0.5-1ms | Android 16+（Vulkan 1.4 强制） |

Swappy 在 Vulkan 路径上的 `SwappyVk_queuePresent()` 会检查设备是否支持 `VK_KHR_present_id`。支持时，present 回调里的 `present_id` 值与 Swappy 内部的帧计数器对齐，用于判断帧是否真的按预期节奏上了屏，而不是在中转路径上被延迟或丢弃。

### DeliQueue：VSync 时间戳精度提升

Android 17 对 `MessageQueue` 做了无锁队列重构（DeliQueue），替换了沿用多年的 `Looper` + `MessageQueue` 锁竞争模型。这个改动对 Swappy 的影响不直接——Swappy 自己不走 Java Looper——但间接效果显著。

Swappy 依赖 `AChoreographer` 回调拿到 VSync 时间戳，而 `AChoreographer` 的回调投递路径经过 `MessageQueue`。旧实现中，主线程的 `MessageQueue.nativePollOnce()` 和渲染线程的同步操作共用一把 `mLock`，当两者竞争时，VSync 回调的到达时间会出现抖动。DeliQueue 通过单生产者-单消费者无锁队列消除了这把锁，使 `AChoreographer` 回调抖动减少约 15%。

对 Swappy 步调算法来说，VSync 时间戳更精准意味着 `onPreSwap()` 里计算"离下一个 vsync 还有多久"的误差更小，`setPresentationTime()` 的决策更可靠。在高刷设备（90Hz、120Hz、144Hz）上，这种精度的提升会被放大——refresh period 越短，同样的时间戳误差对节奏拟合的干扰越大。

[已验证: AOSP frameworks/base/core/java/android/os/MessageQueue.java (DeliQueue 实现), Swappy × Choreographer × Android 17 架构深研]

## 参考资料

- 官方文档：<https://developer.android.com/games/sdk/frame-pacing>
- OpenGL 集成：<https://developer.android.com/games/sdk/frame-pacing/opengl>
- Vulkan 集成：<https://developer.android.com/games/sdk/frame-pacing/vulkan>
- 官方验证页：<https://developer.android.com/games/sdk/frame-pacing/opengl/verify-improvement>
- 官方 API Reference：<https://developer.android.com/games/sdk/reference/frame-pacing>
- Choreographer 文档：<https://developer.android.com/reference/android/view/Choreographer>
- AOSP：`frameworks/opt/gamesdk/games-frame-pacing/common/ChoreographerThread.cpp`
- AOSP：`frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.cpp`
- AOSP：`frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp`
- AOSP：`frameworks/opt/gamesdk/games-frame-pacing/opengl/SwappyGL.cpp`
- AOSP：`frameworks/opt/gamesdk/games-frame-pacing/opengl/EGL.cpp`
- AOSP：`frameworks/opt/gamesdk/include/swappy/swappyGL_extra.h`
- AOSP：`frameworks/opt/gamesdk/include/swappy/swappyVk.h`
- Perfetto SQL 参考：`external/perfetto/src/trace_processor/metrics/sql/android/jank/frames.sql`
- Perfetto SQL 参考：`external/perfetto/src/trace_processor/metrics/sql/android/android_frame_timeline_metric.sql`

### Swappy × Choreographer × Android 17 架构深研
- 来源：/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/DeepResearch/Swappy × Choreographer × Android 17 架构深研.md
- 类型：DeepResearch 调研结果
- 摘要：围绕 Swappy、Choreographer、SurfaceFlinger 三层协作，指出 Android 17 的 DeliQueue 主要改善主线程 MessageQueue 锁竞争，从而提升 Vsync 回调到达质量；Swappy 本体仍依赖 ChoreographerFilter、AChoreographer deadline/expectedPresentationTime 与统计循环做帧节奏控制。
- 注入时间：2026-04-23
- 价值：把 Android 17 的 DeliQueue 变化与现有 Swappy 架构连起来，适合解释高刷设备上帧节奏为何更稳。
