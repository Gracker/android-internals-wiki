---
title: "Frame Pacing Library 与帧节奏控制"
chapter: "2.17"
section: "2.17"
status: "finalized"
applicable_versions: "Android 4.1 (API 16, Java Choreographer 路径) - Android 17 (API 37)"
last_verified: "2026-04-19"
last_verified_against: "frameworks/opt/gamesdk refs/heads/android-games-sdk-games-frame-pacing-release（AGDK frame-pacing release branch，非 Android platform tag）；Perfetto FrameTimeline SQL @ android-17.0.0_r1；frameworks/base DeliQueue @ android-17.0.0_r1；developer.android.com frame-pacing docs"
confidence: medium
drafted_date: "2026-04-06"
drafted_by: "openclaw-task2a"
sources:
  - type: "aosp"
    path: "external/perfetto/src/trace_processor/metrics/sql/android/android_frame_timeline_metric.sql"
  - type: "official"
    path: "developer.android.com/games/sdk/frame-pacing"
tags: ["rendering", "frame-pacing", "swappy", "perfetto", "vulkan"]
related_chapters: ["2.3", "2.6", "2.13", "2.18", "16.4"]
created_by: "task2a-knowledge-gap"
created_date: "2026-04-05"
gap_source: "官方文档 + 研究素材"
task6_state: "reviewed"
task6_result: "pass-light-edit"
task6_reviewed_date: "2026-06-20"
reviewed_by: "openclaw-task6"
reviewed_date: "2026-06-20"
last_task6_at: "2026-06-20T09:06:00+08:00"
last_task6_audit: "2026-06-20"
last_task6_review_log: "logs/review/2026-06-20-09-review.md"
pipeline_stage: "ready-to-publish"
task9_state: "reviewed"
task9_result: "auto-fixed"
task9_task6_reviewed_date: "2026-04-30"
task9_reviewed_date: "2026-06-20"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-06-20T08:27:23+08:00"
last_task9_review_log: "logs/deep-review/2026-06-20-08-deep-review.md"
last_task9_autofix_at: "2026-06-20"
task2b_state: "fixed"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task2b_result: "fixed-lite"
last_task2b_lite_at: "2026-06-20"
last_task2b_at: "2026-05-08T04:51:42.168874+08:00"
review_notes: "2026-05-06 Task9 06:23：deep-review needs-rework；P1 DeliQueue targetSdk 37 边界未收紧；P2 present_wait 依赖说明待补。 | 2026-05-08 Task6 05:05：revisiting→reviewed；修复 frontmatter/source YAML 与轻量措辞，无新增 L3/L4 回炉项，待 Task9 复审。 | 2026-05-08 Task9 05:27：pass-tech-review。P0 0 / P1 0 / P2 2；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-20 Task9 闲时抽检：needs-rework。P0 1 / P1 1 / P2 1；Android 17 tag 下 MessageQueue 路径已拆分，正文旧路径与 mLock 表述错误；frameworks/opt/gamesdk 关键源码锚点仍依赖 main，未证明进入 Android 17，已写入 queue。 | 2026-06-20 Task9 复审：auto-fixed。DeliQueue 路径/targetSdk 37 边界已闭环；Swappy 源码锚点从 main 收紧为 AGDK frame-pacing release branch，并明确不作为 Android 17 platform 源码结论；queue 项已关闭，回到 Task6 复审。 | 2026-06-20 Task6 09:06：revisiting→reviewed，auto-promote finalized。Task9 auto-fixed 后复审：L1 全清（0 禁用词/0 高频词/0 翻译腔动词/0 元叙述/0 中英文间距问题），L2 结构完整（开头/节奏/读者引导全过），25 处 [已验证] 标注、0 处 [待验证]，outline 6 锚点全覆盖。无 L3/L4 回炉项。Task9 auto-fixed + queue 0 pending，满足自动晋升条件。"
task9_review_notes: "2026-05-06 Task9 06:23：deep-review needs-rework；P1 DeliQueue targetSdk 37 边界未收紧；P2 present_wait 依赖说明待补。 | 2026-05-08 Task9 05:27：pass-tech-review。P0 0 / P1 0 / P2 2；Task6 已通过且 queue 无 pending，自动晋升 finalized。 | 2026-06-20 Task9 闲时抽检：needs-rework。P0 1 / P1 1 / P2 1；Android 17 tag 下 MessageQueue 路径已拆分，正文旧路径与 mLock 表述错误；frameworks/opt/gamesdk 关键源码锚点仍依赖 main，未证明进入 Android 17，已写入 queue。 | 2026-06-20 Task9 复审：auto-fixed。DeliQueue 路径/targetSdk 37 边界已闭环；Swappy 源码锚点从 main 收紧为 AGDK frame-pacing release branch，并明确不作为 Android 17 platform 源码结论；queue 项已关闭，回到 Task6 复审。"
last_task9_audit: "2026-06-20"
last_task9_audit_at: "2026-06-20T07:28:47+08:00"
last_task9_audit_log: "logs/deep-review/2026-06-20-07-audit.md"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-20
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
  当前 OpenGL 实现的主链是 `insertSyncFence()` -> `onPreSwap()` -> `setPresentationTime()` -> `swapBuffers()` -> `onPostSwap()`。正文用伪代码或分段引用表达调用顺序，避免把 synthetic snippet 标成单个真实函数。

- 🔹 **Choreographer / DisplayManager 的回退路径**：[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/ChoreographerThread.cpp, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.cpp]
  当前实现分为 public API 和内部线程回退两层。`SwappyGL_init()` / `SwappyVk_initAndGetRefreshCycleDuration()` 仍要求 JNI env 和 Activity；初始化成功后，内部才会在 NDK Choreographer、Java Choreographer 和 no-Choreographer best effort 之间选择。`SwappyDisplayManager` 只在 API 28-30 的一部分路径里启用。

- 🔹 **Auto 模式与多刷新率是动态求解**：[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.h]
  `calculateSwapInterval()` 按 `frameTime / refreshPeriod` 求 interval，用 `REFRESH_RATE_MARGIN = 500ns` 做取整边界，`mAutoSwapIntervalThreshold` 默认是 `50ms`。正文避免写成 11ms / 16ms / 22ms 这类硬编码档位表。

- 🔹 **OpenGL / Vulkan / 非游戏场景的接入边界**：[已验证: frameworks/opt/gamesdk/include/swappy/swappyGL.h, frameworks/opt/gamesdk/include/swappy/swappyVk.h, developer.android.com/reference/android/view/Choreographer]
  OpenGL 需要在 `SwappyGL_swap()` 主线外补 `SwappyGL_setWindow(window)`；Vulkan 也要在 `SwappyVk_queuePresent(VkQueue, const VkPresentInfoKHR*)` 之外补 `SwappyVk_setWindow(device, swapchain, window)`，这样 frame-rate vote / display timing 才接完整。非游戏场景如果只想借鉴节奏控制，`Choreographer.FrameCallback` 示例也要写成可运行的自引用形式。

- 🔹 **验证路径不能只盯 Perfetto**：[已验证: developer.android.com/games/sdk/frame-pacing/opengl/verify-improvement, developer.android.com/games/sdk/reference/frame-pacing, external/perfetto/src/trace_processor/metrics/sql/android/jank/frames.sql]
  官方验证页仍把 `systrace.py` 和 `SurfaceView` channel 作为入口。Swappy 自己还有 `SwappyGL_enableStats()` / `SwappyVk_enableStats()`、`FrameStatistics` logcat 和 `SwappyStats`。Perfetto 的 `Expected Timeline` / `Actual Timeline` 和对应 SQL 则是 Android 12+ 的 FrameTimeline 能力，`SurfaceView` 仍要走替代观察路径。

### 扩展（可选深入）

- 🔸 **与 ARR 的关系**：Swappy 会投票 frame rate 或选择 display mode，平台级 Adaptive Refresh Rate 的模式切换细节放到 §2.18 展开。
- 🔸 **引擎集成的表述边界**：Unity / Unreal 的版本线变化很快，没有 release note 支撑时，不把“默认启用”写成事实。
<!-- outline-end -->

> **源码版本说明**：`frameworks/opt/gamesdk` 仓库在 `android-17.0.0_r1`、`android-16.0.0_r1`、`android-15.0.0_r1` 下均无 `games-frame-pacing` 目录。本文 Swappy 源码引用基于 `refs/heads/android-games-sdk-games-frame-pacing-release`，这是 AGDK 库 release branch，不是 Android 17 platform tag。下文未带 tag 的 `frameworks/opt/gamesdk` 锚点均指向该分支，只用于说明 AGDK Swappy 库实现，不作为 Android 17 platform 源码结论。

## 帧节奏问题在 trace 里长什么样

一个常见误判场景是：游戏逻辑层每秒产出 60 帧，监控面板上的平均 FPS 也是 60，但屏幕是 90Hz。90Hz 的 refresh period 大约是 11.11ms，60FPS 的 frame time 大约是 16.67ms，这两个节奏没有整数倍关系。如果应用只是“画完就交”，屏幕侧会出现一部分帧只占 1 个 refresh period，另一部分帧占 2 个 refresh period。肉眼看到的效果，就是同样 60FPS，运动仍然发颤。

官方文档把这类问题拆成两层。一个是 late frame，帧来晚了，显示系统只能把旧帧再放一次。另一个是 frame arrive too early，提交过早，buffer queue 被塞深，输入到显示的延迟被拉长。Swappy 针对的就是这两层：一层控制 submit 时机，另一层控制 queue 深度。[已验证: developer.android.com/games/sdk/frame-pacing]

排查 trace 时，检查两处：

- `SurfaceView` channel 的 buffered frames 是否稳定。官方 verify-improvement 页面给的判断方法就是这里。
- `Expected Timeline` 和 `Actual Timeline` 是否等宽、是否保持稳定。`Actual Timeline` 忽长忽短，通常说明 frame pacing 本身已经乱了；`Expected Timeline` 很稳、`Actual Timeline` 却频繁 miss deadline，更多是 app 或 SF 侧的执行超时。

[图：同一段游戏滚动场景在启用 Swappy 前后的 trace 对比。上半部分是 `SurfaceView` channel 的 buffered frames，未接入 Swappy 时在 1、2、3 之间来回波动；下半部分是 `Expected Timeline` / `Actual Timeline`，接入后 `Actual Timeline` 的宽度和起止位置更稳定。]

## Swappy 的真实提交链

AGDK frame-pacing release branch 的 OpenGL 路径已经拆成多段。`SwappyGL::swapInternal()` 负责把几个步骤串起来，fence、presentation time 和统计逻辑分散在 `SwappyGL.cpp`、`EGL.cpp`、`SwappyCommon.cpp` 里。

按该 release branch 源码整理，提交顺序可以写成这段伪代码。AOSP 没有原样函数体，所以这里不能标成真实函数。

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

这条链里有三件事。

一件是 `insertSyncFence()`。`EGL.cpp` 里会创建 `EGL_SYNC_FENCE_KHR`，再把 fence 交给内部 waiter thread 异步等待。后面的 `lastFrameIsComplete()` 和 `getFencePendingTime()`，都依赖这里采到的状态。[已验证: frameworks/opt/gamesdk/games-frame-pacing/opengl/EGL.cpp, frameworks/opt/gamesdk/games-frame-pacing/opengl/EGL.h]

一件是 `onPreSwap()` / `onPostSwap()`。这部分在 `SwappyCommon` 里处理等待、统计 frame duration、决定 auto swap interval、更新 presentation time，还会在合适的时候向平台投票新的 frame rate。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp]

还有一件是 `setPresentationTime()`。`SwappyGL.cpp` 不会直接调用 `eglPresentationTimeANDROID()`，而是先比较“离下一个 vsync 还有多久”和当前 display timing，再决定要不要设置 presentation time。离 vsync 太近时，源码直接返回 `EGL_TRUE`，不再额外设置。[已验证: frameworks/opt/gamesdk/games-frame-pacing/opengl/SwappyGL.cpp]

把这几步合在一起看，Swappy 做的事就清楚了：它同时在管 fence、submit 时机、presentation time 和 refresh-rate vote。

## Choreographer / DisplayManager 的回退路径

当前实现最容易被写错的地方，是把内部 `ChoreographerThread` 回退树直接当成 public API contract。公开入口和内部线程策略需要分开看。`SwappyGL_init(JNIEnv*, jobject)` 和 `SwappyVk_initAndGetRefreshCycleDuration(JNIEnv*, jobject, ...)` 的公开入口都要求 JNI env 和 Activity；`vm == nullptr` 这条分支描述的是内部线程选择策略，不能推导成应用可以把 Swappy 当成一套通用的 no-JVM、native-only 初始化 API。

`ChoreographerThread::createChoreographerThread()` 本身的回退链还是很重要，因为它决定了初始化成功之后，Swappy 在内部到底靠哪条节拍源工作。

- `vm == nullptr`，或者 `sdkInt >= 24`，优先 `NDKChoreographerThread`。源码里 `NDKChoreographerThread::MIN_SDK_VERSION = 24`。
- `sdkInt < 24` 且 JVM、Activity 都在，尝试 `JavaChoreographerThread`。
- Java 路径初始化也失败时，回退 `NoChoreographerThread`，日志里会写 `Using no Choreographer (Best Effort)`。
- `Type::App` 这条特殊分支会直接走 `NoChoreographerThread`，表示调用方自己管理 App Choreographer 节拍。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/ChoreographerThread.cpp]

刷新率和 display mode 的路径会随 API 变化。`SwappyDisplayManager::MIN_SDK_VERSION = 28`，`useSwappyDisplayManager()` 还额外做了版本过滤：API 28 到 30 的一部分路径会启用 Java 侧 DisplayManager 帮手；API 31 及以上关闭这条路径，因为 NDK 已经有 refresh-rate callback；源码还单独排除了 Android 11 preview 1 的半成品状态。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.cpp, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.h]

把“公开接入前提”和“内部节拍来源”拆开之后，版本边界更好记：

| 平台边界 | 公开接入前提 | 内部节拍来源 | 刷新率相关辅助 |
|---|---|---|---|
| API 16-23 | `SwappyGL_init()` 仍要求 JVM / Activity，公开主线是 OpenGL | Java Choreographer | 无 NDK Choreographer，Swappy 走 Java 回调 |
| API 24-27 | OpenGL 仍走 `SwappyGL_init()`；Vulkan 路径从这里开始成立 | NDK Choreographer 优先 | 无 `SwappyDisplayManager` |
| API 28-30 | 同上 | NDK Choreographer 优先 | `SwappyDisplayManager` 可维护 supported refresh periods 和 display mode |
| API 31+ | 同上 | NDK Choreographer + native refresh-rate callback | Java DisplayManager helper 退出主链 |

这组边界可以直接拿来排查初始化问题：API 16-23 先确认 JVM / Activity 是否齐全；API 24+ 再看 NDK Choreographer、DisplayManager 和 refresh-rate callback 这几条辅助链。公开文档在 `developer.android.com/games/sdk/frame-pacing`，源码主仓库在 `platform/frameworks/opt/gamesdk`。

## Auto 模式与多刷新率是动态求解

把 Auto 模式理解成 90FPS / 45FPS / 30FPS 三档阈值表，会和当前代码对不上。`SwappyCommon::calculateSwapInterval(frameTime, refreshPeriod)` 的逻辑很直接：

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

这段代码说明：interval 按实际 frame time 和 refresh period 动态计算，代码里没有写死三档模板。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp]

多刷新率选择也是动态过程。`setPreferredRefreshPeriod()` 会遍历 `mSupportedRefreshPeriods`，找“能装下当前 frame time 的最短 swap duration”，同时在满足条件的 refresh config 里尽量选更长的 refresh period 来省电。平台支持 `ANativeWindow_setFrameRate()` 时，Swappy 直接投票 frame rate；没有这条 native 能力时，才退回 DisplayManager 路径。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp]

源码里有几个常量，但含义和三档阈值表不同：

- `mAutoSwapIntervalThreshold` 默认是 `50ms`，慢到这个区间后，auto swap interval 不再主动 sleep，直接让应用尽快跑。
- `REFRESH_RATE_MARGIN` 是 `500ns`，只用于 interval 取整边界。
- `FrameDurations` 的采样窗口是 `2s`，用来估计最近一段 frame duration 走势。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.h, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyCommon.cpp]

在 90Hz 设备上做心算，22ms 左右的 frame time 会被 `calculateSwapInterval()` 算成 2 个 refresh period，得到约 22.22ms 的展示节奏。这个数来自运行时计算，不来自配置表里的“45FPS 档位”。

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

Vulkan 的接入要多几步。`swappyVk.h` 给出的主线是：先让 Swappy 决定 device extensions，再初始化 swapchain 级别状态，之后才在 present 路径上接管 `vkQueuePresentKHR()`。`SwappyVk_queuePresent()` 的真实签名如下。

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

游戏引擎的支持情况变化很快。Unity、Unreal 都有 Swappy 相关入口，但“哪个版本开始支持”“是否默认启用”这类信息，需要直接查各自 release note 或引擎官方 Android 文档。没有出处支撑时，不把版本号写成事实。

非游戏场景如果只想借鉴 frame pacing 的思路，`Choreographer.FrameCallback` 也要写成能自引用的形式。如果用 lambda 写这段回调，`this` 会指向外层对象，按文意跑不起来。匿名内部类能把 callback 自身传回 `postFrameCallback()`。

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

这段用的是平台 Choreographer，不是 Swappy API。目的仍然是把 CPU 侧的 render loop 绑到 display 节拍上。[已验证: developer.android.com/reference/android/view/Choreographer]

## 验证路径：SurfaceView、Perfetto、FrameStatistics 三条线一起看

官方 verify-improvement 页面给的第一条路是 `systrace.py`。抓 trace 时，文档建议把 `sched`、`freq`、`gfx`、`view`、`sync`、`binder_driver`、`hal`、`input`、`aidl` 这些类别一起开出来，然后去看 `SurfaceView` channel。

```bash
python systrace.py -a your-app-package-name -o mygametrace.html \
  sched freq idle am wm gfx view sync binder_driver hal input aidl
```

官方给出的判断口径也很直白：启用 Swappy 之后，`SurfaceView` channel 里 buffered frames 的波动应该收敛下来。[已验证: developer.android.com/games/sdk/frame-pacing/opengl/verify-improvement, developer.android.com/games/sdk/frame-pacing/vulkan/verify-improvement]

验证入口按版本拆开后是这样：

| 平台边界 | 优先观察项 | 说明 |
|---|---|---|
| API 16-30 | `systrace.py`、`SurfaceView` buffered frames、SwappyStats | 这一路没有 FrameTimeline track，也没有 `actual_frame_timeline_slice` / `expected_frame_timeline_slice` |
| API 31+（普通窗口） | 上述三条 + `Expected Timeline` / `Actual Timeline` + trace processor SQL | 可以直接用 FrameTimeline 看 app / sf jank 归因 |
| API 31+（`SurfaceView` 游戏） | 仍以 `SurfaceView` buffered frames、`gpu.renderstages`、SwappyStats 为主 | Perfetto 文档明确写着 `SurfaceViews are currently not supported` |

第二条路是 Perfetto 的 FrameTimeline。这条路要求 Android 12 (S)+，UI 里才会出现 `Expected Timeline` 和 `Actual Timeline`，trace processor 里才有 `actual_frame_timeline_slice` 与 `expected_frame_timeline_slice`。在 Android 10-11 上排查时，按这套关键字去找只会得到空结果。[已验证: Perfetto 官方文档, https://perfetto.dev/docs/data-sources/frametimeline]

做 trace processor 分析时，可以直接查 `actual_frame_timeline_slice` 和 `expected_frame_timeline_slice`。Perfetto 自己的 SQL metric 已经在用 `on_time_finish`、`jank_type`、`present_type` 这些列。

没有现成 trace 时，可以抓一段 15 秒样本：

```bash
adb shell perfetto -o /data/misc/perfetto-traces/frame-pacing.perfetto-trace -t 15s \
  sched freq idle am wm gfx view binder_driver hal
```

抓完后按这个顺序看 4 条轨道：

- App 进程里的 `Choreographer#doFrame`
- App 进程上方的 `Expected Timeline`
- 同一位置的 `Actual Timeline`
- SurfaceFlinger / `SurfaceView` 相关 channel 的 buffered frames

用一条总览查询把时长、deadline 和归因放在一张表里：

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

`SwappyStats` 里有几组需要重点看的 histogram：

- `idleFrames`，渲染完成后在 compositor queue 里又等了几个 refresh periods。
- `lateFrames`，离目标 presentation time 晚了几个 refresh periods。
- `offsetFromPreviousFrame`，相邻两帧之间隔了多少个 refresh periods。
- `latencyFrames`，从 `recordFrameStart` 到实际 present 经过了多少个 refresh periods。

源码里的 logcat label 是固定的。这几行是 `FrameStatistics.cpp` 实际打印的字段名，角括号里的值由运行时决定：

```text
I/FrameStatistics: == Frame statistics ==
I/FrameStatistics: total frames: <runtime value>
I/FrameStatistics: Buckets: [0] [1] [2] ... [N]
I/FrameStatistics: idle frames: <bucket histogram>
I/FrameStatistics: late frames: <bucket histogram>
I/FrameStatistics: offset from previous frame: <bucket histogram>
I/FrameStatistics: frame latency: <bucket histogram>
```

这组数据可以定位“节奏是否稳定、queue 是否变深、延迟是否被拉长”，适合和 Perfetto 对照看。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/FrameStatistics.cpp, frameworks/opt/gamesdk/include/swappy/swappy_common.h, frameworks/opt/gamesdk/include/swappy/swappyGL_extra.h, frameworks/opt/gamesdk/include/swappy/swappyVk.h]

[图：Perfetto 样例。App 进程中同时展开 `Choreographer#doFrame`、`Expected Timeline`、`Actual Timeline`；SurfaceFlinger 一侧展开 `SurfaceView` channel。图中标出一帧 `jank_type=BufferStuffing` 的位置，以及 buffered frames 从 1 升到 2 后没有及时回落的区间。]

## 版本边界、与 ARR 的关系、常见误区

版本边界最好按三条线一起记：一条是 Java / NDK Choreographer 的接入边界，一条是 `SwappyDisplayManager` 这条 Java helper 什么时候进入又什么时候退出，一条是 AGDK 文档和 AOSP 仓库现在分别放在哪里。把这三条线记住，排查时就不会把 API 级别、库形态和仓库位置混成一团。[已验证: frameworks/opt/gamesdk/games-frame-pacing/common/ChoreographerThread.cpp, frameworks/opt/gamesdk/games-frame-pacing/common/SwappyDisplayManager.h, developer.android.com/games/sdk/frame-pacing]

Swappy 和 §2.18 的 Adaptive Refresh Rate 有关系，但不是同一层。Swappy 解决的是 app submit pacing 和 frame-rate vote，平台 ARR 解决的是硬件 mode switch、policy、SurfaceFlinger 如何跟随活跃内容。把这两层拆开看，trace 里的因果关系更容易区分。

**Swappy 的 frame-rate vote 路径**：Swappy 内部通过 `setPreferredRefreshPeriod()` 计算目标帧率后，实际调用的是 `ANativeWindow_setFrameRate(mWindow, frameRate, ANATIVEWINDOW_FRAME_RATE_COMPATIBILITY_DEFAULT)`（条件是 `mANativeWindow_setFrameRate` 函数指针已加载且 `mWindow` 非 null），否则回退到通过 `SwappyDisplayManager` 设置 DisplayManager 的 preferred mode id。如果应用在同一个 `ANativeWindow` 上同时手动调用了 `Surface.setFrameRate()` 或 `ANativeWindow_setFrameRate()`，后调用的会覆盖先前的 vote。SurfaceFlinger 侧会对同一 layer 上来自不同来源的 frame-rate vote 做合并决策（具体策略见 §2.18），应用层不需要关心合并逻辑，但需要避免 Swappy vote 和手动 vote 互相覆盖导致的节奏不稳定。

常见误区如下。

- 用 `Thread.sleep()` 控帧不够。它既不看 vsync，也不知道 display pipeline 现在有几层 buffer。
- Vulkan 有 `VK_PRESENT_MODE_FIFO_KHR`，也不等于已经拿到了 Android 上这一层的 pacing。Swappy 额外处理的是 Android display timing、refresh callback、stats 和 queue depth。
- 平均 FPS 正常，肉眼依然卡，并不矛盾。帧间隔波动增大时，主观流畅度会明显下降，这就是 frame pacing 这节要处理的问题。

## Vulkan 帧确认路径与 Android 17 DeliQueue

### present_id 与 VK_GOOGLE_display_timing：Swappy Vulkan 路径的真实确认方式

Android 16 设备的 Vulkan 能力基线由 Khronos VP_ANDROID_16_minimums profile 定义（具体 Vulkan 版本要求以正式 CDD 16 为准）。`VK_KHR_present_id` 在 Khronos `vk.xml` 中仍是 ratified KHR 设备扩展，不属于 Vulkan 1.4 核心特性；设备支持时，应用需通过 `VkPhysicalDevicePresentIdFeaturesKHR` 查询并启用。复核 `frameworks/opt/gamesdk` 的 AGDK frame-pacing release branch：`SwappyVk.cpp`、`SwappyVkBase.cpp` 和 `swappyVk.h` 中均未出现 `VK_KHR_present_id` 或 `present_id` 相关代码。Swappy Vulkan 路径的帧上屏确认仍围绕 `VK_GOOGLE_display_timing`、GPU fence、Choreographer 回调和 SwappyStats。

`VK_GOOGLE_display_timing` 提供的是 display 驱动报告的 `presentTimes` 时间戳，经过 SurfaceFlinger 中转。Swappy 用这些时间戳与内部统计做校准。这条路径与 Choreographer 回调路径之间存在调度延迟，但这正是 Swappy 通过 `onPreSwap()` / `onPostSwap()` 统计循环试图补偿的部分。

`VK_KHR_present_id` 本身是给 present 操作打递增 ID 的扩展，不等同于 display driver 返回完成时间戳。即使 Swappy 未来接入该扩展，帧上屏时刻的确认仍然需要 display timing 支持。当前 Swappy Vulkan 路径没有使用 `VK_KHR_present_id`，文档或文章不应把"Vulkan 1.4 可用"写成"Swappy 已接入"。

Swappy 当前未接入 `VK_KHR_present_id` 和 `VK_KHR_present_wait`（前者是后者的启用前置，两者均需通过 `VkPhysicalDevice*FeaturesKHR` 查询）。即使设备支持这些扩展，实际能否减少 present 确认延迟还需 benchmark 验证——设备型号、Android build、GPU 驱动、swapchain present mode、是否启用 `VK_GOOGLE_display_timing` 都会影响结果，不能仅凭扩展声明下结论。

### DeliQueue：Java MessageQueue 的无锁重构

Android 17 对 Java 侧 `MessageQueue` 做了无锁队列重构（DeliQueue），替换了沿用多年的 `Looper` + `MessageQueue` 锁竞争模型。

**对 Java Choreographer 的影响（targetSdk 37+）。** Android 17 behavior changes 明确限定：apps targeting Android 17 (API 37) or higher 才会收到 DeliQueue 的无锁 `MessageQueue` 实现。Legacy `MessageQueue`（`LegacyMessageQueue/MessageQueue.java`）中，`nativePollOnce()` 返回后通过 `synchronized (this)` 保护队列读写，其他线程的 `enqueueMessage()` 也竞争同一把 monitor，锁竞争会导致 VSync 回调到达时间抖动。DeliQueue（`CombinedDeliMessageQueue/MessageQueue.java`）通过多生产者 lock-free Treiber stack + Looper 侧 min-heap 的无锁结构消除了这把 monitor（详见 §16.4）。只有 targetSdk ≥ 37 且运行在 Android 17+ 设备上的应用，使用 Java `Choreographer.FrameCallback` 时才会直接受益。targetSdk < 37 的应用即使跑在 Android 17 上，MessageQueue 仍走原有锁路径。

**对 Swappy 的 NDK AChoreographer 路径，影响需要分两层看。** Swappy 的 Vulkan/OpenGL 路径走的是 NDK `AChoreographer` 回调，不直接经过 Java `MessageQueue`。DeliQueue 改造的是 Java 层 `MessageQueue`，目前没有 AOSP commit 或公开文档证明 NDK `AChoreographer` / `ALooper` 的回调路径也做了同样的无锁改造。如果 NDK AChoreographer 的底层仍然走传统 `Looper` 管道，DeliQueue 改善的是 Java 侧回调抖动，不直接传导到 Swappy native 回调。

DeliQueue 改造的是 Java 层 `MessageQueue`。NDK `AChoreographer` / `ALooper` 的回调路径是否做了同样的无锁改造，目前没有公开文档确认——如果 NDK 路径也同步改造，Swappy `onPreSwap()` 中对下一个 VSync 的时间估算精度会受益，高刷设备上效果更明显。

[已验证: AOSP frameworks/base/core/java/android/os/CombinedDeliMessageQueue/MessageQueue.java, frameworks/base/core/java/android/os/LegacyMessageQueue/MessageQueue.java @ android-17.0.0_r1; Swappy × Choreographer × Android 17 架构深研]

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
- 来源：DeepResearch 调研。围绕 Swappy、Choreographer、SurfaceFlinger 三层协作，指出 Android 17 的 DeliQueue 主要改善主线程 MessageQueue 锁竞争，从而提升 Vsync 回调到达质量；Swappy 本体仍依赖 ChoreographerFilter、AChoreographer deadline/expectedPresentationTime 与统计循环做帧节奏控制。
