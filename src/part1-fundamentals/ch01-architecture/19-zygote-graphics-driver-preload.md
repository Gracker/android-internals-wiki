---

title: "Zygote 图形驱动预加载与启动性能"
chapter: "1.19"
section: "1.19"
status: finalized
drafted_date: "2026-05-16"
applicable_versions: "Android 13 (API 33) - Android 17 (API 37)"
last_verified: "2026-05-16"
last_verified_against: "AOSP android-17.0.0_r1"
confidence: medium
tags: [zygote, app-startup, gpu-driver, graphics, gralloc, preload]
related_chapters: ["1.11", "2.10", "8.2", "16.2"]
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/AOSP结构"
material_paths:
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-07-zygote-preloadappprocesshals-preloadgraphicsdriver.md"
  - "cs.android.com frameworks/base/core/java/com/android/internal/os/ZygoteInit.java"
  - "cs.android.com frameworks/base/core/jni/com_android_internal_os_ZygoteInit.cpp"
  - "cs.android.com frameworks/base/core/java/android/os/GraphicsEnvironment.java"
task6_reviewed_date: "2026-05-27"
sources:
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/jni/com_android_internal_os_ZygoteInit.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/GraphicsEnvironment.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/hwui/apex/jni_runtime.cpp @ android-13.0.0_r1 / android-14.0.0_r1 / android-15.0.0_r1 / android-16.0.0_r1 / android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/libs/ui/GraphicBufferMapper.cpp @ android-13.0.0_r1 / android-14.0.0_r1 / android-17.0.0_r1"
  - type: obsidian
    path: "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-07-zygote-preloadappprocesshals-preloadgraphicsdriver.md"
reviewed_date: 2026-07-02
reviewed_by: openclaw-task6
review_round: 2
task6_state: reviewed
task6_result: pass-light-edit
task9_state: reviewed
pipeline_stage: ready-to-publish
task6_review_notes: 2026-05-27 Task6：回炉复审通过。07-01 22 Task6 revisiting：pass-light-edit。Task9 auto-fixed P1:1 已确认（版本锚点迁移至 android-17.0.0_r1，口径闭合）；禁用词零命中；outline 7/7 覆盖；无新增 L1/L2/L3/L4 问题。待 Task9 最终确认 auto-fixed → pass-tech-review 后可自动晋升。07-02 01 Task6 revisiting：pass-light-edit。L1 零命中；L2 开头、节奏、结构均通过；outline 7/7 覆盖。Task9 auto-fixed（P0:0 P1:1-auto-fixed），queue.json 无 pending，自动晋升 finalized。
last_task6_at: 2026-07-02T01:10:00+08:00
last_task6_review_log: "logs/review/2026-05-27-19-review.md"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task9_result: auto-fixed
task2b_result: "fixed-lite"
task2b_state: fixed
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-07-02"
last_task9_at: "2026-07-02T00:28:41+08:00"
last_task9_review_log: "logs/deep-review/2026-07-02-00-deep-review.md"
task9_review_notes: "2026-05-27 Task9：pass-tech-review。复核 ZygoteInit preload 顺序、GraphicBufferMapper preloadHal、zygote_preload_graphics Android 13-16 分支、GraphicsEnvironment chooseDriverInternal；18 点 AUTO-FIX 后口径正确。 P0 0 / P1 0 / P2 0；Task6 已通过且 queue.json 无 pending，自动晋升 finalized。 | 2026-07-01 20 Task9 deep-review: auto-fixed。P0 0 / P1 1(auto-fixed) / P2 0；将主线验证锚点从 Android 16 + AOSP main 迁到 AOSP android-17.0.0_r1，Graphics mapper / Zygote preload / GraphicsEnvironment 口径已闭合，回到 Task6 复审。 | 2026-07-02 00 Task9 deep-review: auto-fixed。P0 0 / P1 1(auto-fixed) / P2 0；修正正文残留 Android 16 主线标签为 Android 17，源码锚点与 android-17.0.0_r1 闭合，回到 Task6 复审。"
last_task2b_lite_at: "2026-05-27"
last_task9_autofix_at: "2026-07-02"
last_task9_audit: "2026-06-14"
last_task6_audit: "2026-06-15"
p0: 0
p1: 1
p2: 0
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-09
---


# 1.19 Zygote 图形驱动预加载与启动性能

<!-- outline-start -->
## 要点

### 🔹 为什么图形驱动预加载属于启动性能问题
从 App 冷启动、首帧提交、GPU driver 首次加载成本三个角度说明问题边界，区分 Zygote 通用 preload 与应用自己的初始化。

### 🔹 ZygoteInit.preload() 中的图形相关节点
梳理 `PreloadAppProcessHALs`、`PreloadGraphicsDriver`、`preloadSharedLibraries`、`WebViewFactory.prepareWebViewInZygote()` 的相对顺序，以及 Perfetto / log 中能看到的观察点。

### 🔹 nativePreloadAppProcessHALs() 的 HAL 选择原则
解释为什么当前优先覆盖大多数 App 进程都会触达、且适合在 fork 前预热的图形 HAL；说明不应把厂商私有 HAL 预加载推成通用结论。

### 🔹 maybePreloadGraphicsDriver() 与禁用开关
说明 `ro.zygote.disable_gl_preload` 的作用、适用场景和风险：预加载可以降低子进程首次图形调用成本，但驱动兼容问题可能影响 zygote 启动。

### 🔹 Updatable GPU Driver 与 GraphicsEnvironment
整理 system driver、updatable driver、ANGLE / game driver 选择路径，说明它们与 Zygote preload 的关系：preload 解决首次加载成本，driver selection 决定加载哪套库。

### 🔹 对 App 启动分析的影响
给出 trace 分析口径：如何区分 zygote 预热收益、App 首帧 GPU 初始化、SurfaceFlinger 合成等待和应用主线程初始化成本。

### 🔹 版本与设备边界
按 Android 13-17、OEM driver 包、SELinux / vendor 配置差异整理验证边界，避免把单一设备表现写成平台规律。

## 扩展

### 🔸 与 1.11 Zygote 机制的交叉引用
Zygote fork、preloaded-classes、资源预加载详见 1.11 节；这里聚焦图形 mapper HAL 与 GPU driver 预加载。

### 🔸 与 8.2 App 启动全流程的交叉引用
首帧阶段的实际观测、ApplicationStartInfo 与启动阶段归因详见 8.2 节；这里只保留和图形驱动相关的分析口径。

### 🔸 驱动预加载异常的排查入口
补充 SELinux denial、driver package、vendor EGL / Vulkan 库加载失败时的日志与降级策略。

<!-- outline-end -->

## 图形驱动预加载解决首帧前的冷路径成本

App 冷启动的前半段由系统进程和 Zygote 完成，后半段才进入应用进程自己的 `ActivityThread`、主线程初始化和首帧绘制。图形驱动预加载夹在这两段之间：它发生在 Zygote 进程启动期，目标是把大多数 App 首次走到图形栈时会触发的库加载、HAL 查询和驱动初始化成本提前到 fork 之前。

这类成本会落到启动体验上，因为首帧前通常要完成窗口创建、`ViewRootImpl` 注册、RenderThread 初始化、EGL / Vulkan 入口调用、buffer 申请和提交。某台设备上如果 GPU driver 首次加载慢，trace 里可能表现为 RenderThread 或应用主线程在首帧附近出现额外等待；如果同一台设备已经通过 Zygote 预热，子进程继承的是一部分已经加载过的只读代码页和进程状态，首帧附近的抖动会小一些。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/com/android/internal/os/ZygoteInit.java]

这里不能把“预加载”理解成提前创建某个 App 的图形上下文。Zygote 没有应用包名、窗口、Surface，也不会替某个 App 分配首帧 buffer。它能做的是加载通用库、预热 mapper HAL、触发一次低成本的图形驱动入口。App 进程 fork 之后，具体使用 system driver、updatable driver 还是 ANGLE，仍由应用进程里的 `GraphicsEnvironment.setup()` 决定。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/GraphicsEnvironment.java]

## Zygote preload 中有两个图形节点

Android 17 的 `ZygoteInit.preload()` 里，图形相关节点位于资源预加载之后、共享库和字体预加载之前。这段代码的重点是调用顺序：`nativePreloadAppProcessHALs()` 先执行，`maybePreloadGraphicsDriver()` 后执行。

```java
bootTimingsTraceLog.traceBegin("PreloadResources");
Resources.preloadResources();
bootTimingsTraceLog.traceEnd();
Trace.traceBegin(Trace.TRACE_TAG_DALVIK, "PreloadAppProcessHALs");
nativePreloadAppProcessHALs();
Trace.traceEnd(Trace.TRACE_TAG_DALVIK);
Trace.traceBegin(Trace.TRACE_TAG_DALVIK, "PreloadGraphicsDriver");
maybePreloadGraphicsDriver();
Trace.traceEnd(Trace.TRACE_TAG_DALVIK);
preloadSharedLibraries();
preloadTextResources();
```

这段顺序给 trace 分析提供了两个锚点：`PreloadAppProcessHALs` 对应图形 mapper HAL 预热，`PreloadGraphicsDriver` 对应 GPU driver 预热。它们属于 Zygote 启动阶段，不属于某个 App 的冷启动切片。分析 App 启动耗时时，要先看设备是否刚开机、Zygote 是否已经完成 preload，再判断首帧附近的 GPU 初始化是否仍在应用进程中发生。

`preloadSharedLibraries()` 在两个图形节点之后加载 `android`、`jnigraphics` 和条件性的 `compiler_rt`。`WebViewFactory.prepareWebViewInZygote()` 更靠后，用于 WebView 在 Zygote 中可共享的初始化。WebView 也可能影响 App 启动，但它和本节的 GPU driver preload 是两条不同路径，trace 中不要合并归因。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/com/android/internal/os/ZygoteInit.java]

## AppProcess HAL 预加载当前落在 GraphicBufferMapper

`nativePreloadAppProcessHALs()` 的 JNI 实现很短：调用 `android::GraphicBufferMapper::preloadHal()`，然后留下扩展注释。注释给出两个准入条件：总是 passthrough，并且被大多数 App 进程加载。

```cpp
void android_internal_os_ZygoteInit_nativePreloadAppProcessHALs(JNIEnv* env, jclass) {
    android::GraphicBufferMapper::preloadHal();
    // Add preloading here for other HALs that are (a) always passthrough, and
    // (b) loaded by most app processes.
}
```

这个选择很克制。Zygote 进程是所有普通 App 进程的父进程，放进这里的 HAL 会影响全局启动、内存和兼容性；只有覆盖面足够大、加载行为足够稳定、适合 fork 前共享的 HAL，才适合进入这条路径。厂商私有 HAL、只服务特定硬件能力的 HAL、依赖应用上下文或权限状态的 HAL，都不该从单机 trace 推成平台规律。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/com_android_internal_os_ZygoteInit.cpp]

`GraphicBufferMapper::preloadHal()` 的版本边界分为两段：Android 13 tag 只预加载 Gralloc 2/3/4 mapper；Android 14 tag 到 Android 17 tag 已包含 Gralloc 5。构造 `GraphicBufferMapper` 时，运行时会从当前分支支持的最高 mapper 版本往前尝试，选中设备可用的实现。

```cpp
void GraphicBufferMapper::preloadHal() {
    Gralloc2Mapper::preload();
    Gralloc3Mapper::preload();
    Gralloc4Mapper::preload();
    Gralloc5Mapper::preload();
}

GraphicBufferMapper::GraphicBufferMapper() {
    mMapper = std::make_unique<const Gralloc5Mapper>();
    if (mMapper->isLoaded()) {
        mMapperVersion = Version::GRALLOC_5;
        return;
    }
    // Older mapper versions are tried after this.
}
```

这段代码验证了一个边界：这里预热的是 graphics mapper / gralloc mapper 入口，不是提前为 App 创建 `GraphicBuffer`，也不是提前映射某个具体 buffer 的 dma-buf。buffer 分配、导入、lock/unlock 仍发生在应用和系统图形管线运行时。预加载减少的是 HAL 发现和库加载的冷路径成本。[已验证: AOSP android-13.0.0_r1 / android-14.0.0_r1 / android-17.0.0_r1, frameworks/native/libs/ui/GraphicBufferMapper.cpp]

## Graphics driver 预加载由系统属性兜底

`maybePreloadGraphicsDriver()` 只做一件事：读取 `ro.zygote.disable_gl_preload`。属性为 `false` 时调用 `nativePreloadGraphicsDriver()`；属性为 `true` 时跳过预加载。

```java
private static final String PROPERTY_DISABLE_GRAPHICS_DRIVER_PRELOADING =
        "ro.zygote.disable_gl_preload";

private static void maybePreloadGraphicsDriver() {
    if (!SystemProperties.getBoolean(PROPERTY_DISABLE_GRAPHICS_DRIVER_PRELOADING, false)) {
        nativePreloadGraphicsDriver();
    }
}
```

`nativePreloadGraphicsDriver()` 的 Java 注释说明了设计意图：通过一次 OpenGL 或 Vulkan 调用加载并初始化 graphics driver；调用本身应当低成本、无状态，首次之后再次调用基本等价于空操作。JNI 层把它转到 `zygote_preload_graphics()`。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/com/android/internal/os/ZygoteInit.java][已验证: AOSP android-17.0.0_r1, frameworks/base/core/jni/com_android_internal_os_ZygoteInit.cpp]

`zygote_preload_graphics()` 位于 `frameworks/base/libs/hwui/apex/jni_runtime.cpp`。Android 13/14 的分支较窄：HWUI 选择 SkiaGL 时调用 `eglGetDisplay(EGL_DEFAULT_DISPLAY)`，选择 Vulkan 时调用 `vkEnumerateInstanceVersion()`。Android 15/16 在 Vulkan 分支后又检查 `Properties::initializeGlAlways()`；该属性为真时，即使 HWUI 使用 Vulkan，也会额外调用一次 `eglGetDisplay(EGL_DEFAULT_DISPLAY)`，为仍使用 GL 的 App 预热 GL driver。[已验证: AOSP android-13.0.0_r1 / android-14.0.0_r1 / android-15.0.0_r1 / android-16.0.0_r1 / android-17.0.0_r1, frameworks/base/libs/hwui/apex/jni_runtime.cpp]

这个开关的价值在异常设备上更明显。GPU driver 属于强厂商相关组件，某些 vendor EGL / Vulkan 实现如果不适合在 Zygote 期加载，失败会影响所有 App 进程的父进程。`ro.zygote.disable_gl_preload=true` 给 OEM 留出降级入口：牺牲首个图形调用的预热收益，换取 Zygote 启动稳定性。[待验证: 具体厂商触发条件需要实机日志或 vendor issue]

## GraphicsEnvironment 决定应用进程最终使用哪套 driver

Zygote preload 和 `GraphicsEnvironment` 处理的是两层问题。前者提前触发通用图形栈的冷路径；后者在应用进程启动后，根据系统属性、全局设置、应用包名、allowlist / denylist、debug 状态和 manifest metadata，决定当前 App 使用哪套 driver。

Android 17 的 `GraphicsEnvironment.setup()` 里有三段 trace 名称：`setupGpuLayers`、`setupAngle`、`chooseDriver`。它们都发生在应用进程里，适合和 App 首帧 trace 一起看。

```java
Trace.traceBegin(Trace.TRACE_TAG_GRAPHICS, "setupGpuLayers");
setupGpuLayers(context, coreSettings, pm, packageName, appInfoWithMetaData);
Trace.traceEnd(Trace.TRACE_TAG_GRAPHICS);

Trace.traceBegin(Trace.TRACE_TAG_GRAPHICS, "setupAngle");
if (setupAngle(context, coreSettings, pm, packageName)) {
    mShouldUseAngle = true;
    setGpuStats(ANGLE_DRIVER_NAME, ANGLE_DRIVER_VERSION_NAME, ANGLE_DRIVER_VERSION_CODE,
            0, packageName, getVulkanVersion(pm));
}
Trace.traceEnd(Trace.TRACE_TAG_GRAPHICS);

Trace.traceBegin(Trace.TRACE_TAG_GRAPHICS, "chooseDriver");
if (!chooseDriver(context, coreSettings, pm, packageName, appInfoWithMetaData)) {
    if (!mShouldUseAngle) {
        setGpuStats(SYSTEM_DRIVER_NAME, SYSTEM_DRIVER_VERSION_NAME,
                SYSTEM_DRIVER_VERSION_CODE,
                SystemProperties.getLong(PROPERTY_GFX_DRIVER_BUILD_TIME, 0),
                packageName, getVulkanVersion(pm));
    }
}
Trace.traceEnd(Trace.TRACE_TAG_GRAPHICS);
```

`chooseDriverInternal()` 的第一层保护是系统组件排除：privileged app 以及未更新的 system app 会直接回退到 system driver，避免驱动更新影响预装系统组件。对其余应用，`UPDATABLE_DRIVER_ALL_APPS` 可以关闭 updatable driver，也可以把普通应用整体导向 production driver；prerelease driver 还要满足 debuggable 或 manifest metadata 允许。随后再看 production opt-out、prerelease opt-in、production opt-in、production denylist 和 production allowlist。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/GraphicsEnvironment.java]

updatable driver 生效后，`chooseDriver()` 会拼出 driver APK 的 native library 搜索路径，并读取 APK assets 里的 `sphal_libraries.txt`，通过 `setDriverPathAndSphalLibraries()` 交给 native 层。这里的 `sphal` 指 Same-Process HAL 相关 linker namespace，不是业务层的“单点”概念。[已验证: AOSP android-17.0.0_r1, frameworks/base/core/java/android/os/GraphicsEnvironment.java]

```java
final String sphalLibraries = getSphalLibraries(context, driverPackageName);
setDriverPathAndSphalLibraries(paths, sphalLibraries);

private String getSphalLibraries(Context context, String driverPackageName) {
    final Context driverContext =
            context.createPackageContext(driverPackageName, Context.CONTEXT_RESTRICTED);
    final BufferedReader reader = new BufferedReader(new InputStreamReader(
            driverContext.getAssets().open(UPDATABLE_DRIVER_SPHAL_LIBRARIES_FILENAME)));
    // Each asset line is joined into the sphal library list.
}
```

这也解释了为什么启动分析不能只盯 `PreloadGraphicsDriver`。如果 App 被强制走 ANGLE，或命中 updatable production driver，应用进程内的 driver 选择、namespace 设置、debug layer 配置仍会出现在首帧前。Zygote 预热只能减少一部分共性冷路径，不能替代 per-app driver selection。

## App 启动 trace 要拆成四段看

遇到“首帧前 GPU 初始化很慢”的问题，可以把 trace 拆成四段，逐段排除。

| 观察段 | 典型位置 | 主要问题 | 证据 |
| --- | --- | --- | --- |
| Zygote preload | boot trace 的 zygote 进程 | `PreloadAppProcessHALs` 或 `PreloadGraphicsDriver` 是否耗时异常 | `Trace.TRACE_TAG_DALVIK` 切片、zygote log |
| App driver selection | App 进程启动早期 | `setupGpuLayers`、`setupAngle`、`chooseDriver` 是否耗时或失败 | `Trace.TRACE_TAG_GRAPHICS` 切片、GraphicsEnvironment log |
| 首次图形 API 调用 | RenderThread / GLThread / Vulkan 初始化线程 | EGL / Vulkan driver 是否在 App 进程内冷加载 | so 加载、EGL/Vulkan log、线程阻塞点 |
| 首帧提交与合成 | App、SurfaceFlinger、HWC | buffer dequeue/queue、fence、合成等待是否拖慢首帧 | FrameTimeline、SurfaceFlinger、HWC / fence 切片 |

这四段对应不同修复方向。Zygote preload 慢，优先看设备级属性、vendor driver 兼容性和 boot trace；`GraphicsEnvironment` 慢，优先看 ANGLE、updatable driver、debug layer 和全局设置；首次 EGL / Vulkan 调用慢，优先看应用是否延迟到了首帧附近才创建渲染上下文；SurfaceFlinger 或 HWC 等待慢，要回到 2.6、2.10、2.15、2.16 节的渲染管线和 fence 分析。

对 App 团队来说，最有价值的动作不是关闭系统预加载，而是把自己的首帧图形工作拆清楚：窗口 attach、RenderThread 启动、EGLContext 创建、shader / pipeline 初始化、首个 buffer 提交分别耗时多少。Zygote 的收益只能从系统侧减掉一段公共成本，应用自己的图形初始化仍要按 App 启动专项处理。详见 8.2 节。

## 版本、设备和验证边界

本文以 AOSP android-17.0.0_r1 为主线验证基线，Android 13-16 只用于历史版本差异。`ZygoteInit.preload()` 中的 `PreloadAppProcessHALs`、`PreloadGraphicsDriver`，以及 `GraphicsEnvironment` 的 updatable driver 选择路径，均已在 Android 17 源码中核对。`GraphicBufferMapper::preloadHal()` 的 Gralloc 2/3/4/5 预加载顺序以 android-17.0.0_r1 为准。[已验证: AOSP android-17.0.0_r1]

版本边界按下面口径使用：

| 范围 | 可确认内容 | 边界 |
| --- | --- | --- |
| Android 13-14 | `zygote_preload_graphics()` 已覆盖 SkiaGL 的 `eglGetDisplay()` 与 Vulkan 的 `vkEnumerateInstanceVersion()`；Android 13 的 mapper 预加载停在 Gralloc 2/3/4 | Android 14 起 mapper 预加载包含 Gralloc 5 |
| Android 15-17 | Vulkan 分支可因 `Properties::initializeGlAlways()` 额外预热 GL driver | 是否走这条分支取决于 HWUI 属性和设备配置 |
| Android 16 | `GraphicsEnvironment` 包含 ANGLE、updatable production / prerelease driver、`sphal_libraries.txt` 读取 | settings 名称和 OEM 默认值由系统镜像决定 |
| Android 17 | `GraphicBufferMapper::preloadHal()` 预加载 Gralloc 2/3/4/5 mapper | 设备最终加载哪个 mapper 取决于 vendor 实现 |
| OEM 设备 | `ro.zygote.disable_gl_preload`、`ro.gfx.driver.*`、vendor EGL / Vulkan 包会改变行为 | 需要 boot trace、属性快照、logcat 和 driver 包信息交叉验证 |

AOSP 已能闭合 `zygote_preload_graphics()` 的平台调用边界；仍需实测的是不同 SoC、不同 vendor EGL / Vulkan 包在这些调用上的耗时和失败模式。

## 排查入口

设备侧排查可以从四类信息开始：

- 系统属性：`getprop ro.zygote.disable_gl_preload`、`getprop ro.gfx.driver.0`、`getprop ro.gfx.driver.1`、`getprop ro.gfx.driver_build_time`，用于确认预加载和 updatable driver 的全局状态。
- boot trace：抓取包含 zygote 的启动 trace，搜索 `PreloadAppProcessHALs`、`PreloadGraphicsDriver`、`preloadSharedLibraries`，用于判断耗时是否发生在系统启动期。
- App trace：搜索 `setupGpuLayers`、`setupAngle`、`chooseDriver`、RenderThread 首次 EGL / Vulkan 调用和首帧 FrameTimeline，区分 driver selection 与首帧渲染成本。
- logcat / SELinux：过滤 `Zygote`、`GraphicsEnvironment`、`EGL`、`Vulkan`、`avc: denied`，用于判断 driver package、sphal library、vendor 库加载或权限配置是否失败。

如果某台设备关闭 `ro.zygote.disable_gl_preload` 后启动稳定性恢复，只能说明该设备的 zygote 期图形预加载有兼容性风险；不能推出所有设备都应关闭。平台默认路径仍是预加载开启，异常设备按 vendor driver 和系统镜像配置单独处理。
