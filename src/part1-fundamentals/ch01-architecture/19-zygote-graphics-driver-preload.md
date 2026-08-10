---
title: Zygote 图形栈预加载与首帧冷路径
chapter: '1.19'
section: '1.19'
status: finalized
applicable_versions: Android 13 (API 33) - Android 17 (API 37)
last_verified: '2026-07-25'
last_verified_against: AOSP android-17.0.0_r1 + Android 17 API 37 official documentation
confidence: high
sources:
  - type: official
    path: "https://source.android.com/docs/core/graphics"
  - type: official
    path: "https://source.android.com/docs/core/graphics/arch-vulkan"
  - type: official
    path: "https://source.android.com/docs/core/graphics/implement-vulkan"
  - type: official
    path: "https://developer.android.com/games/guidelines"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/jni/com_android_internal_os_ZygoteInit.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/hwui/apex/jni_runtime.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/native/libs/ui/GraphicBufferMapper.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/GraphicsEnvironment.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/graphics/java/android/graphics/HardwareRenderer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/RenderProxy.cpp @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/libs/hwui/renderthread/RenderThread.cpp @ android-17.0.0_r1"
tags:
  - android
  - zygote
  - app-startup
  - hwui
  - renderthread
  - egl
  - vulkan
  - angle
  - gralloc
  - gpu-driver
related_chapters:
  - '1.11'
  - '2.10'
  - '8.2'
  - '16.2'
drafted_date: "2026-05-16"
created_by: "task2a-knowledge-gap"
created_date: "2026-05-16"
gap_source: "素材驱动/AOSP结构"
material_paths:
  - "OpenClaw定时任务/AutoResearchClaw调研报告/2026-05-07-zygote-preloadappprocesshals-preloadgraphicsdriver.md"
  - "cs.android.com frameworks/base/core/java/com/android/internal/os/ZygoteInit.java"
  - "cs.android.com frameworks/base/core/jni/com_android_internal_os_ZygoteInit.cpp"
  - "cs.android.com frameworks/base/core/java/android/os/GraphicsEnvironment.java"
task6_reviewed_date: "2026-05-27"
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
last_deepseek_cn_review_at: 2026-07-03
---

# 1.19 Zygote 图形栈预加载与首帧冷路径

Android 会在 Zygote 派生应用进程前预先触达一部分图形栈。这项工作不会替应用绘制首帧；它把多数应用都会遇到的 HAL 发现、动态库映射和图形入口冷路径挪到系统启动阶段。

这里有两个常见误解：

1. Zygote 调过一次 EGL 或 Vulkan，App 就不需要再初始化 RenderThread 和图形 context。
2. Zygote 预加载了“GPU driver”，每个应用使用的 driver 就已经确定。

Android 17 源码都不支持这两个结论。要看清收益和边界，需要把图形初始化拆成四段：

```text
系统启动
  └─ Zygote preload
       ├─ GraphicBufferMapper HAL 预热
       └─ system graphics loader/driver 入口预热

应用 bindApplication
  └─ GraphicsEnvironment.setup()
       ├─ debug layers
       ├─ ANGLE 选择
       └─ system / updatable driver 选择

Activity 即将创建
  └─ HardwareRenderer.preload()
       ├─ 启动 RenderThread
       └─ 创建 GL 或 Vulkan context

窗口与首帧
  └─ CanvasContext / Surface / BufferQueue / fence / SurfaceFlinger
```

四段发生在不同进程、不同线程，修复手段也不同。

## 1. Zygote 预加载转移了什么成本

普通应用进程由匹配其 ABI 的 Zygote 派生。Zygote 派生进程前映射的共享库代码页，以及适合继承的只读状态，可以由后续子进程复用；同一个 Zygote 只需承担一次冷加载成本。

图形预加载主要覆盖：

- graphics mapper HAL 的发现与加载。
- EGL 或 Vulkan 加载器/驱动的一段低成本入口路径。
- fork 后可共享的库映射和页面缓存收益。

它明确不覆盖：

- 某个应用的 driver allowlist / denylist 选择。
- 应用的 EGLContext、VkInstance、VkDevice 或 VkPipeline。
- Surface、BLASTBufferQueue 和具体 `GraphicBuffer`。
- shader 编译、pipeline cache miss 和应用资源上传。
- SurfaceFlinger 合成、HWC validate/present 和 fence 等待。

所以，Zygote 预加载只能削减公共冷路径，不能消灭首帧图形初始化。

### 1.1 这笔成本从 App 启动移到了 boot

预加载开启时：

```text
boot / Zygote 多做一次通用初始化
                   ↓
多个 App 少走一部分重复冷路径
```

预加载关闭时：

```text
Zygote 启动可能更轻
                   ↓
首次使用相应图形路径的 App 自行承担更多成本
```

这是系统级摊销，并非没有代价。评估时要同时测 boot 与 App 启动，不能只截取一张应用 trace。

## 2. Android 17 的 Zygote preload 顺序

`android-17.0.0_r1` 的 `ZygoteInit.preload()` 关键顺序如下：

```text
beginPreload()
preloadClasses()
cacheNonBootClasspathClassLoaders()
Resources.preloadResources()
nativePreloadAppProcessHALs()
maybePreloadGraphicsDriver()
preloadSharedLibraries()
preloadTextResources()
preloadCompatConfig()
HttpEngine.preload()          # 受 flag 控制
WebViewFactory.prepareWebViewInZygote()
endPreload()
warmUpJcaProviders()
```

其中两个图形切片使用 `Trace.TRACE_TAG_DALVIK`：

```java
Trace.traceBegin(Trace.TRACE_TAG_DALVIK, "PreloadAppProcessHALs");
nativePreloadAppProcessHALs();
Trace.traceEnd(Trace.TRACE_TAG_DALVIK);

Trace.traceBegin(Trace.TRACE_TAG_DALVIK, "PreloadGraphicsDriver");
maybePreloadGraphicsDriver();
Trace.traceEnd(Trace.TRACE_TAG_DALVIK);
```

几个边界值得单独记住：

- `PreloadAppProcessHALs` 先于 `PreloadGraphicsDriver`。
- `preloadSharedLibraries()` 在二者之后；Android 17 还会按 flag 预加载 `perfetto_framework_jni`。
- WebView 的 Zygote 初始化在后面，是另一条共享内存与启动优化路径。
- 这些切片属于系统启动期间的 Zygote，不属于某个 App 的 `bindApplication` 或 `launchingActivity`。

应用启动跟踪里通常没有这两个切片，需要采集包含 Zygote 的 boot trace 才能看到。

## 3. `PreloadAppProcessHALs` 当前只预热 GraphicBufferMapper

JNI 实现非常克制：

```cpp
void android_internal_os_ZygoteInit_nativePreloadAppProcessHALs(
        JNIEnv* env, jclass) {
    android::GraphicBufferMapper::preloadHal();
    // Add preloading here for other HALs that are (a) always passthrough, and
    // (b) loaded by most app processes.
}
```

方法名是复数，但 Android 17 当前只调用 `GraphicBufferMapper::preloadHal()`。源码注释给未来扩展设了两个条件：

1. HAL 总是以 same-process / passthrough 方式加载。
2. 大多数应用进程都会使用。

Zygote 是所有普通 App 的父进程。把一个低覆盖率或依赖应用身份的 HAL 放进这里，会增加 boot、常驻映射和 fork 安全风险。因此，不能因为某个厂商 HAL 首次加载慢，就推导出“应该放进 Zygote 预加载”。

### 3.1 Android 17 不再无条件预加载 Gralloc 2/3

Android 14–16 的实现可以简写为：

```cpp
Gralloc2Mapper::preload();
Gralloc3Mapper::preload();
Gralloc4Mapper::preload();
Gralloc5Mapper::preload();
```

这对 Android 14–16 成立，对 Android 17 不完整。当前实现是：

```cpp
static bool requireMapper4() {
    return android_get_device_api_level() >= 36
            && flags::require_gralloc4_or_newer();
}

void GraphicBufferMapper::preloadHal() {
    if (!requireMapper4()) {
        Gralloc2Mapper::preload();
        Gralloc3Mapper::preload();
    }
    Gralloc4Mapper::preload();
    Gralloc5Mapper::preload();
}
```

对应关系如下：

- Gralloc 4/5 始终参与预加载。
- 只有不要求 Mapper 4+ 的设备才预加载 Gralloc 2/3。

构造 `GraphicBufferMapper` 时同样先尝试 Gralloc 5，再尝试 Gralloc 4；允许 legacy mapper 时才继续回退到 3/2。若设备被要求使用 Mapper 4+，但 4/5 都不可用，源码会 `LOG_ALWAYS_FATAL`，不会静默退回旧 mapper。

### 3.2 预热 mapper 不等于分配 buffer

`preloadHal()` 没有宽高、format、usage 或 native handle。它无法：

- 为首帧分配 `GraphicBuffer`。
- 导入某个 DMA-BUF。
- 执行 lock/unlock。
- 建立 App 与 SurfaceFlinger 之间的 BufferQueue。

`PreloadAppProcessHALs` 很快，只能说明 mapper 预热没有明显卡住；据此无法判断首帧 buffer 分配是否顺畅。

## 4. `PreloadGraphicsDriver` 只触达低成本入口

Java 层先检查一个只读系统属性：

```java
private static final String PROPERTY_DISABLE_GRAPHICS_DRIVER_PRELOADING =
        "ro.zygote.disable_gl_preload";

private static void maybePreloadGraphicsDriver() {
    if (!SystemProperties.getBoolean(
            PROPERTY_DISABLE_GRAPHICS_DRIVER_PRELOADING, false)) {
        nativePreloadGraphicsDriver();
    }
}
```

属性缺省为 false，也就是默认执行预加载。JNI 再调用：

```cpp
zygote_preload_graphics();
```

Android 17 的 native 分支由 HWUI pipeline 决定：

```cpp
if (Properties::peekRenderPipelineType()
        == RenderPipelineType::SkiaGL) {
    eglGetDisplay(EGL_DEFAULT_DISPLAY);
} else {
    uint32_t apiVersion;
    vkEnumerateInstanceVersion(&apiVersion);

    if (Properties::initializeGlAlways()) {
        eglGetDisplay(EGL_DEFAULT_DISPLAY);
    }
}
```

这段分支只触发所选图形后端的早期 loader 路径；它没有创建应用的 context、surface 或交换链。

### 4.1 GL 分支没有创建 EGLContext

`eglGetDisplay(EGL_DEFAULT_DISPLAY)` 让 EGL 加载器/驱动走到 display 获取路径，但源码没有调用：

- `eglInitialize()`
- `eglChooseConfig()`
- `eglCreateContext()`
- `eglCreateWindowSurface()`
- `eglMakeCurrent()`

因此，“Zygote 已初始化应用的 GL context”这一说法不成立。实际的 context 仍在子进程的 RenderThread 创建。

### 4.2 Vulkan 分支没有创建 VkInstance 或 VkDevice

`vkEnumerateInstanceVersion()` 查询 loader 支持的 instance API 版本，不需要 `VkInstance`。这条路径同样没有：

- `vkCreateInstance()`
- 枚举并选择物理设备。
- `vkCreateDevice()`
- 创建 queue、swapchain 或 pipeline。

它预热的是 Vulkan 加载器/驱动入口，不包含完整的 Vulkan 运行时状态。

### 4.3 Vulkan HWUI 也可能顺便预热 GL

`Properties::initializeGlAlways()` 读取 `debug.hwui.initialize_gl_always`，默认值来自 HWUI flag。当 HWUI 使用 SkiaVulkan，但设备上仍有大量 App 直接使用 GLES 时，这个分支会额外调用一次 `eglGetDisplay()`。

源码说明，这次 GL 调用发生在 fork 前，相关内存应可共享；不使用 GL 的应用不需要在自己的启动路径再次承担同样的公共成本。

## 5. `ro.zygote.disable_gl_preload` 不是 App 调优开关

这个属性容易被误用。需要先看清三点：

1. 它只跳过 `maybePreloadGraphicsDriver()`。
2. 它不会跳过 `nativePreloadAppProcessHALs()`，mapper HAL 仍会预热。
3. `ro.*` 是只读属性，普通 App 不能在运行时切换。

要对比开关效果，平台/OEM 团队需要准备不同系统镜像或启动属性配置，并重启 Zygote/设备。在已经启动的设备上执行 `setprop` 后立即重跑应用，不能构成有效的 A/B 对比。

关闭它适合用作设备级兼容性止损，例如某个厂商 EGL/Vulkan 实现在 fork 前的入口调用中崩溃、死锁或触发不可继承状态。后续仍应修复驱动或系统集成问题；永久关闭会把冷路径成本还给应用进程。

## 6. 应用进程仍要执行 `GraphicsEnvironment.setup()`

App fork 后，`ActivityThread.handleBindApplication()` 会在应用代码加载前调用：

```text
setupGraphicsSupport(appContext)
  └─ GraphicsEnvironment.getInstance().setup(...)
```

Android 17 的 `GraphicsEnvironment.setup()` 有四个连续 trace：

```text
setupGpuLayers
setupAngle
chooseDriver
notifyGraphicsEnvironmentSetup
```

前三个决定当前进程的图形环境；末尾一个主要用于向 `GameManager` 通知 `GameManager`。

### 6.1 `setupGpuLayers`：调试 layer

它处理 Vulkan/GLES / GLES debug layer 的搜索路径和选择。量产 non-debuggable App 不能随意加载外部调试代码；debuggable 状态、目标包名、全局设置和 manifest metadata 共同约束这条路径。

如果启动回归只出现在安装了 validation layer 或图形抓帧工具的测试环境，应先排除这一层，再判断是否与 Zygote preload。

### 6.2 `setupAngle`：选择 GLES 实现

ANGLE 不是“另一块 GPU driver”。它把 OpenGL ES 调用翻译到其他后端，在 Android 上通常与 Vulkan 驱动配合。Android 17 会综合以下条件进行选择：

- 全局/per-app ANGLE 设置。
- `persist.graphics.egl` 与 `ro.hardware.egl`。
- 设备、全局和动态 denylist。
- game category 与设备资源配置。
- manifest 的 `com.android.graphics.driver.prefer_angle`。

Android 17 对 manifest opt-in 还有设备门槛：essential tier、low-RAM 设备或 `ro.vendor.api_level < 202604` 时，不会按该 metadata 启用。“manifest 写了 prefer_angle”不代表所有 Android 17 设备都会采用 ANGLE。

### 6.3 `chooseDriver`：system 与 updatable driver

`chooseDriverInternal()` 先排除：

- privileged App。
- 未更新的 system App。

这类组件继续使用 system driver，避免驱动更新破坏关键系统组件。

对普通 App，选择优先级是：

```text
UPDATABLE_DRIVER_ALL_APPS
  > production opt-out
  > prerelease opt-in
  > production opt-in
  > production denylist
  > production allowlist
```

当前属性名：

```text
ro.gfx.driver.0   # production driver package
ro.gfx.driver.1   # prerelease driver package
```

选择 updatable driver 后，framework 会：

1. 确认 driver package 是 system package。
2. 检查 `targetSdk` 与当前 ABI。
3. 拼出 native library 和 APK 内 `lib/<abi>` 的搜索路径。
4. 读取 APK 的 `assets` 目录中的 `sphal_libraries.txt`。
5. 调用 `setDriverPathAndSphalLibraries()` 配置 native loader。

这一步发生在每个应用进程。Zygote 触达过系统 EGL/Vulkan 入口，但不会替应用选择可更新驱动包路径、ANGLE 包或调试层。

## 7. 启动 RenderThread 的是 `HardwareRenderer.preload()`

`ActivityThread.handleLaunchActivity()` 在创建硬件加速 Activity 之前调用：

```java
if (ThreadedRenderer.sRendererEnabled
        && (activityInfo.flags
                & ActivityInfo.FLAG_HARDWARE_ACCELERATED) != 0) {
    int tid = HardwareRenderer.preload();
    // 随后把 RenderThread TID 告诉 ActivityManager 调整调度。
}
```

`HardwareRenderer.preload()` 的 Android 17 注释很直接：

源码注释原文为 “Start render thread and initialize EGL or Vulkan.”

它要求 `GraphicsEnvironment.chooseDriver()` 已完成。native 路径如下：

```text
HardwareRenderer.preload()
  └─ RenderProxy::preload()
       ├─ RenderThread::getInstance()
       │    └─ 创建并启动 "RenderThread"
       └─ 向 RenderThread queue 投递 RenderThread::preload()
```

`RenderThread::preload()` 再按 HWUI pipeline 分支：

```cpp
if (SkiaGL) {
    queue().post([this]() {
        ATRACE_NAME("earlyPreloadGlContext");
        requireGlContext();
    });
} else {
    requireVkContext();
}
HardwareBitmapUploader::initialize();
```

这一步与 Zygote 预加载的区别是：

| Zygote | App RenderThread |
| --- | --- |
| `eglGetDisplay()` | `EglManager::initialize()`、创建 GL context 与 Skia `GrDirectContext` |
| `vkEnumerateInstanceVersion()` | `VulkanManager::initialize()`、创建 Vulkan/Skia context |
| 没有应用与窗口 | 已确定 App driver，准备实际渲染 |
| boot 期间一次 | 每个需要硬件加速的 App 进程执行 |

`HardwareRenderer.preload()` 把任务投到 RenderThread，使 driver/context 初始化尽量与主线程创建 Activity 的过程重叠。若预热尚未完成，首帧仍可能在 RenderThread 或 UI→RT 同步点等待。

## 8. 首帧阶段还有哪些 Zygote 帮不了的成本

即使前面三段都很快，首帧仍可能卡在：

### 8.1 Surface 与 BufferQueue

`ViewRootImpl`、`ThreadedRenderer` 和 `CanvasContext` 需要绑定有效 Surface，设置 BLASTBufferQueue，建立生产者/消费者关系。这里涉及 Binder、SurfaceControl 事务和 buffer slot，仅加载驱动无法完成这些工作。

### 8.2 buffer allocation / import

Gralloc 映射器已预热，不代表分配器也已预热。首次分配还可能经过：

- `GraphicBufferAllocator` 初始化。
- allocator HAL Binder 调用。
- DMA-BUF heap 分配。
- mapper import 与 metadata 校验。

Android 17 的 `HardwareRenderer.preInitBufferAllocator()` 专门把 allocator singleton 初始化放到异步任务里，因为低资源设备上的这段工作可能阻塞首帧。分析时要区分 mapper 与 allocator。

### 8.3 shader 与 pipeline

Skia、GL 或 Vulkan 首次创建 shader/pipeline、加载持久化 cache、上传纹理和字体 atlas，都是 per-App 或 per-driver-cache 成本。Zygote 没有应用资源，无法提前完成。

### 8.4 提交、fence 与合成

App 已经画完，不代表画面已经显示。首帧还要经过：

```text
queueBuffer
  → SurfaceFlinger latch
  → composition strategy
  → HWC / GPU composition
  → present fence
  → display
```

这条链路慢时，修改 Zygote preload 没有针对性。

## 9. Trace 应按四个进程/线程域分析

| 域 | 关键切片 / 事件 | 回答的问题 |
| --- | --- | --- |
| Zygote / boot | `PreloadAppProcessHALs`、`PreloadGraphicsDriver` | 系统是否在启动期间负责预热，哪一段慢 |
| App main / bind | `setupGraphicsSupport`、`setupGpuLayers`、`setupAngle`、`chooseDriver` | 当前应用选择了什么环境，选择是否异常耗时 |
| RenderThread | `earlyPreloadGlContext`、EGL/Vulkan/Skia 初始化 | context 是否在首帧前完成，是否仍有 driver 冷路径 |
| App + SurfaceFlinger | FrameTimeline、BufferQueue、fence、latch、present | 首帧是否卡在提交或合成 |

### 9.1 不要用一个 `dlopen` 解释全部耗时

driver 初始化可能包含：

- 动态链接与 relocation。
- 打开 `/dev` 节点。
- ioctl/Binder 查询。
- 读取配置与 cache。
- 启动 driver 内部线程。
- shader compiler 或 pipeline cache 初始化。

只看到 `libGLES*.so` 或 Vulkan 动态库映射，不能推断耗时全在 loader。需要对齐 CPU slice、I/O、Binder、sched 和调用栈。

### 9.2 App main 与 RenderThread 可能并行

`HardwareRenderer.preload()` 主要投递 RenderThread 工作，不表示主线程同步完成全部 GPU 初始化。跟踪中要看：

- App main 何时调用 preload。
- RenderThread 何时开始 `earlyPreloadGlContext` 或 Vulkan init。
- 首帧 sync/draw 是否追上尚未完成的预热。

主线程切片很短、首帧仍慢时，问题可能已经转移到 RenderThread。

## 10. 设备侧核查

### 10.1 记录属性和全局选择

下面的属性和全局设置共同描述 Zygote 预加载开关、HWUI pipeline 以及可更新 driver/ANGLE 选择：

```bash
adb shell getprop ro.zygote.disable_gl_preload
adb shell getprop debug.hwui.renderer
adb shell getprop debug.hwui.initialize_gl_always
adb shell getprop ro.hardware.egl
adb shell getprop ro.gfx.driver.0
adb shell getprop ro.gfx.driver.1
adb shell getprop ro.gfx.driver_build_time

adb shell settings get global updatable_driver_all_apps
adb shell settings get global angle_gl_driver_all_angle
adb shell settings get global angle_gl_driver_selection_pkgs
adb shell settings get global angle_gl_driver_selection_values
```

这些值应与 trace 同时保存。只截取 `chooseDriver` 耗时、不记录最终配置，无法比较两台设备。

### 10.2 检查当前 App 实际映射

在 userdebug/root 或具备调试权限的环境中：

```bash
adb shell cat /proc/<PID>/maps \
  | grep -E 'libEGL|libGLES|libvulkan|angle|graphics'
```

这能证明“哪些库已映射”，但不能单独证明“所有 GL/Vulkan 调用最终由哪套驱动处理”。还要结合 `GraphicsEnvironment` 日志、属性、driver package 和 API trace。

### 10.3 日志入口

下面的日志筛选用于查找 Zygote 预加载、driver 选择、动态链接和 SELinux 拒绝信息：

```bash
adb logcat -v threadtime \
  | grep -E 'Zygote|GraphicsEnvironment|EGL|Vulkan|RenderThread|avc: denied'
```

重点看：

- updatable / ANGLE package 不存在或 ABI 不匹配。
- `sphal_libraries.txt` 读取失败。
- driver metadata 缺失。
- linker namespace 或 SELinux 拒绝。
- EGL/Vulkan loader fallback。

日志没有错误，也不能排除性能问题；耗时仍以 trace 为准。

## 11. 如何进行有效的 A/B 对比

要评估 `ro.zygote.disable_gl_preload` 或 mapper 预热变化，至少控制：

1. 使用同一硬件、同一 ABI、同一系统/厂商构建版本，只改变目标配置。
2. 两组都从完整 reboot 开始，让对应 Zygote 重建。
3. 等待 boot completed 后再启动测试 App。
4. 保持 ANGLE、updatable driver、HWUI renderer 和 debug layer 配置一致。
5. 分别记录系统启动期间的 Zygote 预加载、应用绑定、RenderThread Zygote preload、App bind、RenderThread init 和 first frame。
6. 报告中位数与高分位，不根据单次 trace 下结论。
7. 同时观察 PSS、共享页和 Zygote 常驻成本，避免只换来时间而忽略内存。

如果关闭预加载后系统启动变快、App 首帧却变慢，这属于成本转移；如果 App 启动没有变化，可能有以下原因：

- 对应驱动已由其他 boot 组件加载。
- App 选择了 ANGLE/updatable driver，没有复用目标路径。
- 文件页仍在 page cache。
- 瓶颈位于着色器、allocator 或 SurfaceFlinger。

没有调用栈与配置证据时，不要猜是哪一种。

## 12. 版本边界

| 版本 | 已确认变化 | 当前写作边界 |
| --- | --- | --- |
| Android 13（API 33） | mapper 预加载 Gralloc 2/3/4；Zygote 按 SkiaGL/Vulkan 分别触达 `eglGetDisplay()` / `vkEnumerateInstanceVersion()` | 没有预加载 Gralloc 5 |
| Android 14（API 34） | mapper preload 加入 Gralloc 5 | 仍按 5→4→3→2 选择可用 mapper |
| Android 15–16 | Vulkan HWUI 分支可通过 `initializeGlAlways()` 额外预热 GL；mapper 仍预热 2/3/4/5 | 是否额外预热 GL 取决于属性/flag |
| Android 17（API 37） | `requireMapper4()` 可在 device API ≥ 36 时跳过 legacy Gralloc 2/3；ANGLE 增加面向 Android 17 设备的 manifest opt-in 与设备门槛 | 当前结论锚定 `android-17.0.0_r1` |

历史差异可用于解释旧设备，但分析 Android 17 时不能继续使用 Android 16 无条件预加载四个版本的代码。

## 13. 常见误区

### “Zygote 已经创建好 EGLContext”

不成立。Zygote 只调用 `eglGetDisplay()`；App RenderThread 才初始化 EGL、创建 context 并构造 Skia context。

### “Vulkan 预加载已经创建 VkDevice”

不成立。Zygote 调用的是 `vkEnumerateInstanceVersion()`。

### “PreloadAppProcessHALs 会预加载所有 App HAL”

不成立。Android 17 当前只预热 GraphicBufferMapper。

### “Android 17 一定预加载 Gralloc 2/3/4/5”

不成立。要求 Mapper 4+ 时会跳过 2/3。

### “Zygote 预加载决定应用使用的驱动”

不成立。App fork 后仍通过 `GraphicsEnvironment.setup()` 选择 ANGLE、system 或 updatable driver。

### “应用可通过关闭 `ro.zygote.disable_gl_preload` 动态调优”

不成立。该属性是只读平台配置，而且关闭它只影响 graphics driver 入口，不影响映射器 HAL 预热。

### “首帧慢就是 driver preload 失效”

不成立。context、allocator、shader、BufferQueue、fence 和合成都可能是主因。

## 14. 检查清单

1. 分清 Zygote、App main、RenderThread 与 SurfaceFlinger 四个时间域。
2. 确认应用由哪个 ABI 的 Zygote fork。
3. boot trace 检查 `PreloadAppProcessHALs` 与 `PreloadGraphicsDriver`。
4. Android 17 mapper Android 17 映射器路径，按 `requireMapper4()` 判断是否包含 Gralloc 2/3。
5. 记录 `ro.zygote.disable_gl_preload` 与 HWUI renderer。
6. App bind 阶段检查 `setupAngle`、`chooseDriver` 和最终 package。
7. 不把 `eglGetDisplay()` 写成 EGLContext 初始化。
8. 不把 `vkEnumerateInstanceVersion()` 写成 Vulkan device 初始化。
9. 检查 `HardwareRenderer.preload()` 是否在首帧前给 RenderThread 留出足够时间。
10. 分开分析映射器与分配器。
11. shader/pipeline、buffer、fence 与合成单独取证。
12. A/B 对比必须重启 Zygote/设备，并保持驱动选择一致。
13. OEM 结论附上 SoC、系统/厂商构建版本、driver package 与属性快照。
14. 当前平台源码统一引用 `android-17.0.0_r1`。

## 参考资料

- [AOSP：Graphics architecture](https://source.android.com/docs/core/graphics)
- [AOSP：Vulkan architecture](https://source.android.com/docs/core/graphics/arch-vulkan)
- [AOSP：Implement Vulkan](https://source.android.com/docs/core/graphics/implement-vulkan)
- [Android Developers：Games guidelines / Android 17 ANGLE opt-in](https://developer.android.com/games/guidelines)
- [AOSP：ZygoteInit.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/com/android/internal/os/ZygoteInit.java)
- [AOSP：com_android_internal_os_ZygoteInit.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/jni/com_android_internal_os_ZygoteInit.cpp)
- [AOSP：zygote_preload_graphics（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/apex/jni_runtime.cpp)
- [AOSP：GraphicBufferMapper.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-17.0.0_r1/libs/ui/GraphicBufferMapper.cpp)
- [AOSP：GraphicsEnvironment.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/GraphicsEnvironment.java)
- [AOSP：ActivityThread.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP：HardwareRenderer.java（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/graphics/java/android/graphics/HardwareRenderer.java)
- [AOSP：RenderProxy.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/RenderProxy.cpp)
- [AOSP：RenderThread.cpp（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/renderthread/RenderThread.cpp)
- [版本演进：GraphicBufferMapper.cpp（android-13.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-13.0.0_r1/libs/ui/GraphicBufferMapper.cpp)
- [版本演进：GraphicBufferMapper.cpp（android-14.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-14.0.0_r1/libs/ui/GraphicBufferMapper.cpp)
- [版本演进：GraphicBufferMapper.cpp（android-16.0.0_r1）](https://android.googlesource.com/platform/frameworks/native/+/refs/tags/android-16.0.0_r1/libs/ui/GraphicBufferMapper.cpp)
- [版本演进：zygote_preload_graphics（android-13.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-13.0.0_r1/libs/hwui/apex/jni_runtime.cpp)
- [版本演进：zygote_preload_graphics（android-15.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-15.0.0_r1/libs/hwui/apex/jni_runtime.cpp)
