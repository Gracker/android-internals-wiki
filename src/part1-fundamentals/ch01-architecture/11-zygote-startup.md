---

title: "Zygote 机制与启动性能优化"
chapter: "1.11"
section: "1.11"
status: "ready-for-review"
drafted_date: "2026-04-05"
drafted_by: "openclaw-task2a"
reviewed_date: "2026-04-18"
reviewed_by: "openclaw-task6"
applicable_versions: "Android 5.0 (API 21) - Android 17 (API 37)"
last_verified: "2026-04-11"
last_verified_against: "AOSP android-17.0.0_r1 (Zygote preload 序列与 android-16 一致，主线以 android-17.0.0_r1 为基准)"
confidence: high
sources:
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/Zygote.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/ZygoteServer.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/ZygoteProcess.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/com/android/internal/os/RuntimeInit.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/ProcessList.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/os/AppZygote.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/webkit/WebViewZygote.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/config/preloaded-classes @ android-17.0.0_r1"
  - type: official
    path: "https://source.android.com/docs/core/runtime/zygote"
  - type: official
    path: "https://developer.android.com/reference/android/app/ZygotePreload"
tags: [zygote, fork, startup, preload, cow, usap, app-zygote, webview]
related_chapters: ["1.2", "1.3", "8.2", "8.3"]
pipeline_stage: "task9_pending"
task9_state: pending
task9_result: needs-rework
last_task9_review_log: logs/deep-review/2026-07-14-17-deep-review.md
last_task9_at: "2026-07-14T17:26:54+08:00"
last_task9_review_notes: "2026-07-14 Task9 deep-review: needs-rework。P0 0 / P1 2。需要修复 USAP 与 Child Zygote 关系描述、16KB 页边界影响数据等问题后重新复审。Round 2: P0=0 / P1=2 (applicable_versions vs last_verified_against 不一致 + frontmatter task9_state 重复字段冲突). P2 1 (USAP 边界前提). queue.json 新增 P95 条目."
finalized_by: openclaw-task9-auto-promote
task6_state: reviewed
task6_result: pass-light-edit
task6_reviewed_date: "2026-07-14"
last_task6_review_log: "logs/review/2026-07-14-19-review.md"
task6_review_notes: "07-14 18 Task6 revisiting：pass-light-edit。L1 小修 1 处（禁用词 链路 → 调用路径）；outline 6/6 覆盖；frontmatter YAML 管道符腐蚀修复 + 过期 task9 重复字段清理。Task9 2026-07-14 needs-rework（P1:2），待 Task9 修复后重新复审。"
last_task9_audit: "2026-05-26"
last_task9_audit_at: "2026-05-26T14:20:00+08:00"
last_task9_audit_log: "logs/deep-review/2026-05-26-14-audit.md"
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-18"
task2b_state: fixed
task2b_result: fixed
repaired_date: "2026-04-24"
repaired_by: "openclaw-task2b"
last_task2b_at: 2026-07-14T18:51:57+08:00
last_task6_audit: "2026-06-24"
last_task6_at: "2026-07-14T19:39:29+08:00"
reviewed_at: "2026-05-18T03:31:27+08:00"
task9_review_log: "logs/deep-review/2026-05-18-03-deep-review.md"
---



# 1.11 Zygote 机制与启动性能优化

<!-- outline-start -->

<!-- AIW-源码调研-2026-05-07 -->
### PreloadAppProcessHALs 与 PreloadGraphicsDriver

ZygoteInit.preload() 包含两条关键预加载路径，分别对应 gralloc mapper HAL 和 GPU 驱动的 zygote 期初始化：

#### nativePreloadAppProcessHALs()

- **源码**:`core/jni/com_android_internal_os_ZygoteInit.cpp` 行 19-22
- **当前实现**:`GraphicBufferMapper::preloadHal()` -- 预加载 gralloc mapper HAL(passthrough 库)
- **实际调用路径**:`ZygoteInit.nativePreloadAppProcessHALs()` → `GraphicBufferMapper::preloadHal()` → `Gralloc2/3/4/5Mapper::preload()`,加载 gralloc mapper 的 passthrough 共享库，让 fork 后的子进程直接继承已加载的 gralloc 库，避免冷启动时重复 dlopen + HAL 初始化开销
- **引入版本**:Android 9(`PreloadAppProcessHALs` 在 `android-9.0.0_r1` 已存在，同时还有 `preloadOpenGL`)

```cpp
void android_internal_os_ZygoteInit_nativePreloadAppProcessHALs(JNIEnv* env, jclass) {
    android::GraphicBufferMapper::preloadHal();
    // Add preloading here for other HALs that are (a) always passthrough, and
    // (b) loaded by most app processes.
}
```

#### nativePreloadGraphicsDriver()

- **源码**:`core/jni/com_android_internal_os_ZygoteInit.cpp` 行 24-26
- **实现**:`zygote_preload_graphics()` -- 内部执行 OpenGL/Vulkan 纯函数调用，触发 GPU 驱动加载
- **控制开关**:`ro.zygote.disable_gl_preload` 系统属性(默认 false,即启用预加载)
- **引入版本**:Android 10(`PreloadGraphicsDriver` 在 `android-10.0.0_r1` 已存在)

```java
private static void maybePreloadGraphicsDriver() {
    if (!SystemProperties.getBoolean(PROPERTY_DISABLE_GRAPHICS_DRIVER_PRELOADING, false)) {
        nativePreloadGraphicsDriver();
    }
}
```

#### Updatable GPU Driver 包路径

- **包名**:`com.android.graphics.driver`
- **选择框架**:`core/java/android/os/GraphicsEnvironment.java`
- **sphal 库列表**:`sphal_libraries.txt` -- 指定必须通过 SP-HAL(Same-Process HAL)命名空间加载的 GL 库，实现驱动的版本隔离和懒加载
- **Driver 类型**:
  - `UPDATABLE_DRIVER_GLOBAL_OPT_IN_PRODUCTION_DRIVER (1)` → 生产 updatable driver
  - `UPDATABLE_DRIVER_GLOBAL_OPT_IN_PRERELEASE_DRIVER (2)` → 预发布 driver
  - `UPDATABLE_DRIVER_GLOBAL_OPT_IN_OFF (3)` → 强制 system graphics driver
- **系统属性**:`ro.gfx.driver.0` (production)、`ro.gfx.driver.1` (prerelease)、`ro.gfx.driver_build_time`

#### 完整 Preload 序列(ZygoteInit.java 行 119-163)

1. `beginPreload()` → `ZygoteHooks.onBeginPreload()`
2. `preloadClasses()` → `/system/etc/preloaded-classes`
3. `cacheNonBootClasspathClassLoaders()` → 非启动类路径 ClassLoader 缓存
4. `preloadResources()` → `Resources.preloadResources()`
5. `nativePreloadAppProcessHALs()` → gralloc mapper HAL 预加载(Android 9 引入)
6. `maybePreloadGraphicsDriver()` → GPU 驱动预加载(Android 10 引入)
7. `preloadSharedLibraries()` → libandroid.so / libjnigraphics.so / libcompiler_rt.so
8. `preloadTextResources()` → Hyphenator.init() + TextView.preloadFontCache()
9. `HttpEngine.preload()` (Android 16 可选)
10. `WebViewFactory.prepareWebViewInZygote()`
11. `warmUpJcaProviders()` → AndroidKeyStoreProvider.install() + JCA provider warm-up

<!-- AIW-源码调研-2026-05-07 END -->

## 要点

### 🔹 锚点 1:Zygote 为什么存在
- 它解决的是"每个 App 都从零初始化 ART 和 framework"这件事太慢的问题
- 核心收益是 preload + COW 共享

### 🔹 锚点 2:从启动到建进程的两段 IPC
- App / Launcher 到 system_server 主要走 Binder
- system_server 把建进程请求交给 Zygote 时，实际走的是 zygote socket / LocalSocket

### 🔹 锚点 3:android-16 的 preload 实际阶段
- `PreloadClasses`
- `CacheNonBootClasspathClassLoaders`
- `PreloadResources`
- `PreloadAppProcessHALs`
- `PreloadGraphicsDriver`
- 以及共享库、文本资源、WebView 预处理

### 🔹 锚点 4:fork 之后到首帧前的可观测路径
- `launching: pkg` 是覆盖整段启动窗口的 span
- 在这段时间窗里观察 `am_proc_start` → `PostFork` → `ActivityThread.main()` → `attachApplication` → `am_proc_bound` → `bindApplication` → 首帧

### 🔹 锚点 5:几类 Zygote 的职责边界
- Primary Zygote、secondary zygote、child zygote
- WebViewZygote
- App Zygote 与 `ZygotePreload`

### 🔹 锚点 6:Zygote 性能分析的边界
- 什么问题属于 Zygote
- 什么问题属于 App 初始化、MessageQueue 或首帧渲染
<!-- outline-end -->

## 为什么要了解 Zygote

如果只把 Zygote 理解成"fork 一个新进程的地方",冷启动 trace 很容易看错。完整冷启动至少分两段：前半段是 Launcher / App 通过 Binder 进入 `system_server`,由 ATMS / AMS 决定是否需要新进程；后半段才是 `system_server` 把建进程请求交给 Zygote。把这两段混在一起，后面就会把 Binder、zygote socket、`bindApplication`、首帧渲染全写乱。

Zygote 对性能的价值，也不是"fork 一次只要几毫秒"这么简单。它做的事，是在系统启动阶段预先装好 ART 运行时、framework 常用类、系统资源和部分共享库，然后让后续子进程通过 Copy-on-Write 共享这些只读页面。这样，冷启动时我们就不用在每个 App 里重复做一遍相同的初始化。

所以理解 Zygote,有三个直接收益：第一，能把"进程创建慢"和"App 初始化慢"分开看；第二，能解释为什么 framework 类加载通常很快，但 `Application.onCreate()` 仍然可能成为瓶颈；第三，能在 Perfetto 里用 `launching: pkg` 圈出整段启动窗口，并把 `am_proc_start`、`PostFork`、`bindApplication` 这些锚点放到同一时间窗观察。

## Zygote 为什么存在

Android 不是传统 Linux 桌面那种"每个进程启动时从零加载运行时"的模型。移动设备对冷启动延迟和内存复用更敏感，如果每个 App 都独立初始化虚拟机、装载 framework 类、解析系统资源，启动成本会非常高。

Zygote 把所有"几乎每个进程都会用到"的公共初始化工作前置到系统启动阶段做一次，然后让后续子进程继承这份状态。`init` 拉起 primary zygote 之后，Zygote 会先完成 preload,再 fork 出 `system_server`,后续普通 App 进程也都从它继续派生。这样做的核心收益有两个。

第一个收益是启动速度。framework 层的常见类、基础资源、共享库已经在内存里，子进程不需要重新把它们装起来。第二个收益是内存效率。子进程刚 fork 出来时，和 Zygote 共享同一批只读页面，只有某个页面第一次被写入时，内核才会真的复制一份出去。这就是 COW(Copy-on-Write)的意义。

在 16KB Page Size 的设备上，COW 的收益会进一步放大。页表条目数量减少约 75%,fork() 复制虚拟地址空间(`dup_mmap`)的耗时随之缩短。这个效果在高内存压力场景更明显--页表越精简，fork 期间需要遍历和复制的 VMA 链表条目就越少。

这一点也决定了 Zygote 优化的边界。它擅长解决"公共初始化不要重复做",但它解决不了 App 自己的业务初始化。你在 `Application.onCreate()` 里主动初始化十几个 SDK,Zygote 并不会替你背锅。

## 从启动到建进程：谁在和 Zygote 通信

从用户点击图标到新进程出现，Launcher / App 到 `system_server` 的通信走 Binder;`system_server` 到 Zygote 的建进程请求走 zygote socket / LocalSocket。

按 AOSP android-17.0.0_r1 的实际代码路径（preload 序列与 android-16 一致），`ProcessList.startProcess(...)` 在 `system_server` 里准备好 UID、GID、ABI、seInfo 等参数后，会调用 `Process.start(...)`。参数组装成启动命令并发给 Zygote 的，由 `android.os.ZygoteProcess` 处理：

```java
// frameworks/base/services/core/java/com/android/server/am/ProcessList.java
startResult = Process.start(...);

// frameworks/base/core/java/android/os/ZygoteProcess.java
return startViaZygote(...);
...
return zygoteSendArgsAndGetResult(openZygoteSocketIfNeeded(abi), ...);
```

这里最关键的是 `openZygoteSocketIfNeeded()` 和 `zygoteSendArgsAndGetResult()`。它们说明 `system_server` 把参数写入 zygote socket,等 Zygote 返回新进程的 PID,而不是通过 Binder 服务调用 Zygote。

工程上这个区分很重要。因为如果问题出在 `startActivity()` 之前或 `system_server` 调度阶段，你更该看 Binder、AMS / ATMS、WindowManager 的时序；如果问题出在建进程之后，就该切到 Zygote 和 App 主线程那条线，不要继续在 Binder 里瞎找。

## android-16 的 preload 具体做了什么

旧文章里经常会把 Zygote preload 简化成"preload classes + preload OpenGL",这在 android-16 上已经不够准确了。按 `ZygoteInit.preload()` 的实际代码，主链至少包括下面这些阶段：

```java
// frameworks/base/core/java/com/android/internal/os/ZygoteInit.java
bootTimingsTraceLog.traceBegin("PreloadClasses");
preloadClasses();
...
bootTimingsTraceLog.traceBegin("CacheNonBootClasspathClassLoaders");
cacheNonBootClasspathClassLoaders();
...
bootTimingsTraceLog.traceBegin("PreloadResources");
Resources.preloadResources();
...
Trace.traceBegin(..., "PreloadAppProcessHALs");
nativePreloadAppProcessHALs();
...
Trace.traceBegin(..., "PreloadGraphicsDriver");
maybePreloadGraphicsDriver();
```

这几个名字要尽量按源码写，不要再回到旧版文章里常见的 `PreloadOpenGL`、`BeginIcuCachePinning` 那套命名。android-17 的 trace 观察点，应该以 `PreloadClasses`、`CacheNonBootClasspathClassLoaders`、`PreloadResources`、`PreloadAppProcessHALs`、`PreloadGraphicsDriver` 为准，后面还会继续执行 `preloadSharedLibraries()`、`preloadTextResources()`,以及 `WebViewFactory.prepareWebViewInZygote()`。

这个命名口径只对应本章验证过的 android-17 基线（经 `android-17.0.0_r1` 复核，preload 主序列与 android-16 一致，全章以 android-17.0.0_r1 为基准）。回看 Android 5-9 或 10-15 时，要按对应版本的 `ZygoteInit.java` 重新确认 preload slice 名，不要直接套用这里的名称。

`PreloadGraphicsDriver` 的边界需要单独说明。`ZygoteInit.java` 对它的注释写得很直白：它通过一次 OpenGL 或 Vulkan 调用把图形驱动装进内存并完成初始化，如果驱动已经在内存里，后续调用基本就是 no-op。**这表示的是驱动 / EGL 层面的预热，不等于"每个 App 的 GPU context 已经创建完成"。** App 侧的 RenderThread、EGL context、Surface 以及首帧绘制，仍然发生在各自进程启动之后。

同样不要把 `preloaded-classes` 想成"所有常用 UI 类都在里面"。它主要是 bootclasspath / framework 侧的高频类。至少在 android-17.0.0_r1 的 `frameworks/base/config/preloaded-classes` 里，并没有 `androidx.recyclerview.widget.RecyclerView` 这种 AndroidX 控件。也就是说，framework 预热和应用侧库预热是两回事。

再补一个经常看错的点：这些 preload trace 发生在 **zygote 进程**,不是 `system_server` 进程。代码就是在 `ZygoteInit.main()` 的 preload 阶段执行的，此时 `system_server` 还没被 fork 出来。所以如果你在开机 trace 里想分析 preload 过慢，不要跑到 `system_server` track 上找这些 slice。

## fork 之后到 Application.onCreate() 之前，实际发生了什么

如果只说"Zygote fork 之后进入 `ActivityThread.main()`",还是太粗了。能指导 Perfetto 分析的路径，先要把普通 zygote fork 和 USAP specialization 分开。

| 路径 | Java 入口 | native 调用 | 是否产生新 PID | `PostFork` 在 trace 里的含义 |
| --- | --- | --- | --- | --- |
| 普通 zygote 路径 | `forkAndSpecialize()` | `nativeForkAndSpecialize()` | 会 | 新 fork 出来的子进程进入后续初始化 |
| USAP 命中路径 | `specializeAppProcess()` | `nativeSpecializeAppProcess()` | 不会 | 已存在的 USAP 进程完成特化后继续启动 |

`PostFork` 只能说明目标应用进程已经进入 post-fork / post-specialize 之后的初始化阶段。它不能单独证明"刚刚发生了一次 native fork"。判断当前启动是否真的走了 fork,还要结合 PID 是否新建、是否命中 USAP pool,以及它和 `am_proc_start` 的相对位置。

普通 zygote 路径里，`forkAndSpecialize()` 的 `nativeForkAndSpecialize()` 会创建子进程，并在**子进程**侧打出 `PostFork` trace:

```java
// frameworks/base/core/java/com/android/internal/os/Zygote.java
int pid = nativeForkAndSpecialize(...);
if (pid == 0) {
    Trace.traceBegin(Trace.TRACE_TAG_ACTIVITY_MANAGER, "PostFork");
}
```

这也是为什么去 `zygote64` 进程里搜索 `fork` slice 不稳。android-16 更稳定的锚点是目标应用进程里的 `PostFork`,但解释它时要先区分上面的两条路径。

如果 system_server 命中了 USAP pool,Zygote 取出的已经是一个现成的 unspecialized 进程。后面的工作重点是 UID / GID / SELinux / nice name 等特化。普通 fork 路径和 USAP 路径在进入 `ZygoteInit.zygoteInit()` 之后汇合。

目标应用进程会走 `ZygoteInit.zygoteInit()`、`RuntimeInit.applicationInit()`，并进入 `ActivityThread.main()`。这条链把"刚创建或刚特化的进程"推进成"可以运行 Android 应用主线程的进程"。

`ActivityThread.main()` 不会立刻执行 `Application.onCreate()`。它会先把主线程 Looper 准备好，然后通过 Binder 调 `attachApplication` 回到 `system_server`。在 android-17.0.0_r1 的 `ActivityThread.java` 里，能看到这一步：

```java
// frameworks/base/core/java/android/app/ActivityThread.java
mgr.attachApplication(mAppThread, startSeq);
```

这一步完成后，AMS / ATMS 才知道"这个新进程真的起来了，可以往里下发绑定和启动事务了"。如果你打开了 Android logs 数据源，通常会看到 `am_proc_start` 先出现，`am_proc_bound` 随后出现。前者表示 AMS 决定起进程，后者表示新进程已经和 `system_server` 建立好绑定关系。

App 主线程收到 `bindApplication` 之后，trace 会进入 `handleBindApplication()`、`ContentProvider` 安装、`Application` 创建和 `Application.onCreate()` 的前半段准备工作：

```java
// frameworks/base/core/java/android/app/ActivityThread.java
Trace.traceBegin(Trace.TRACE_TAG_ACTIVITY_MANAGER, "bindApplication");
handleBindApplication(data);
```

到这里，冷启动的职责边界就清楚了：`PostFork` 更接近 Zygote 孵化阶段，`bindApplication` 更接近 App 初始化阶段。`launching: <package>` 则是 `ActivityMetricsLogger.startLaunchTrace()` 在 `system_server` 侧创建的 async span。它从启动开始一直覆盖到启动窗口结束，会和 `am_proc_start`、`PostFork`、`bindApplication`、首帧这些锚点重叠。看 trace 时，用这个 span 圈出整段启动窗口，并在窗口内部查看各个点状事件的位置。

[图：冷启动时序图，`launching: pkg` 作为覆盖整段启动窗口的 span;在 span 内标出 `am_proc_start` → `PostFork` → `attachApplication` → `am_proc_bound` → `bindApplication` → 首帧 `doFrame`,并区分 system_server、zygote、app main thread 三条轨道]

## 在 Perfetto / logcat 里怎么观察这条链

如果目标是区分"Zygote 问题"还是"App 初始化问题",最实用的方法是把公共锚点串起来看。

第一组锚点来自 Android logs:`am_proc_start` 和 `am_proc_bound`。这两个事件来自 AMS,适合拿来标记"什么时候开始起进程"和"什么时候新进程已经绑定完成"。

```sql
SELECT ts, tag
FROM android_logs
WHERE tag IN ('am_proc_start', 'am_proc_bound')
ORDER BY ts DESC
LIMIT 20;
```

第二组锚点来自系统和应用 trace:`launching: <package>`、`PostFork`、`bindApplication`、首个 `Choreographer#doFrame`。其中 `launching: <package>` 是一段 async span,适合拿来圈定整次启动的时间窗；`PostFork` 和 `bindApplication` 是落在这段时间窗里的阶段锚点。下面这个查询适合在定位单次冷启动时把这些片段拉到同一条时间轴上：

```sql
SELECT
  process.name AS process_name,
  thread.name AS thread_name,
  slice.name,
  CAST(slice.ts / 1e6 AS FLOAT) AS ts_ms,
  CAST(slice.dur / 1e6 AS FLOAT) AS dur_ms
FROM slice
JOIN thread_track ON slice.track_id = thread_track.id
JOIN thread USING (utid)
JOIN process USING (upid)
WHERE slice.name IN ('PostFork', 'bindApplication', 'Choreographer#doFrame')
   OR slice.name GLOB 'launching:*'
ORDER BY slice.ts;
```

用这条链分析时，判断思路通常是这样的：

- `am_proc_start` 到 `PostFork` 很短，但 `bindApplication` 很长，问题大概率在 App 初始化，不在 Zygote。
- `launching: <package>` 覆盖很长，而 span 内的 `bindApplication` 并不长，就要继续看 `system_server` 侧的 Activity 启动事务、窗口切换、首帧上报。
- `PostFork` 到 `bindApplication` 间隔很长，说明 fork / specialize 完成后到 attach / bound 之间有额外等待，可能要回看调度、I/O 或系统负载。

注意一个现实细节，不同厂商 build 的 trace 命名会略有差异，`PostFork` 也可能因为 trace 类别没开全而缺席。如果确实看不到它，不要再退回错误的 `zygote64 + LIKE '%fork%'` 方案，而是退一步用 `am_proc_start`、子进程首次调度、`am_proc_bound`、`bindApplication` 这些更稳的公共锚点去估算边界。

## Primary Zygote、WebViewZygote、App Zygote、child zygote 的边界

这一组概念要和 `openZygoteSocketIfNeeded(abi)` 一起看，否则 `ZygotePreload` 和 USAP 很容易串线。

普通 App 进程先经过 `ZygoteProcess.openZygoteSocketIfNeeded(abi)` 选 socket。它做的判断是"当前请求的 ABI 应该交给哪一个主 zygote 处理"。可以按下面这张表记：

| 目标进程 / ABI | 进入的 socket | 是否属于 primary / secondary 主线 | USAP pool | 说明 |
| --- | --- | --- | --- | --- |
| ABI 命中 primary zygote 支持列表的普通 App 进程 | primary zygote socket | 是 | 可用 | 常见于主 ABI 对应的普通应用进程 |
| ABI 命中 secondary zygote 支持列表的普通 App 进程 | secondary zygote socket | 是 | 可用 | 用于另一套 ABI 的普通应用进程 |
| `android:useAppZygote="true"` 的 isolated service | App Zygote 自己的 socket | 否，属于 child zygote | 不可用 | `ZygotePreload` 只服务这一路 |
| WebView provider / renderer 相关进程 | WebViewZygote 自己的 socket | 否，属于 child zygote | 不可用 | 用来复用 WebView 预热状态 |

`Primary Zygote / secondary zygote` 是系统启动阶段由 `init` 拉起的主孵化器。普通 App 进程和 `system_server` 都从这条主线派生。USAP pool 也只挂在这条主线上。

`child zygote` 是由现有 Zygote 再派生出的次级孵化器。`ZygoteProcess.startChildZygote(...)` 会给它创建独立 socket;`ZygoteInit.childZygoteInit()` 则是它的入口。它的角色是后续继续孵化其他进程的中间层。

`WebViewZygote` 是 child zygote 的一个具体用法。`android.webkit.WebViewZygote` 会通过 `startChildZygote(...)` 拉起名为 `webview_zygote` 的子 zygote,然后调用 `preloadApp(...)` 为当前 WebView provider 预加载代码和数据。它只服务 WebView / Chromium 相关进程。

`App Zygote` 也是 child zygote 的一个具体用法，而且它和 `android.app.ZygotePreload` 绑定得非常紧。`ZygotePreload` 在 Android Developers API reference 中明确标注为 **Added in API level 29**,也就是 Android 10。它对应 `<application android:zygotePreloadName="...">` 指向的类，这个类负责为 **开启了 `android:useAppZygote="true"` 的 isolated service** 预加载应用代码和数据。

这条边界需要单独记住：USAP 只服务 primary / secondary zygote;App Zygote 和 WebViewZygote 都有自己的 child zygote socket,不会从主 zygote 的 USAP pool 里拿进程。

[图：Primary Zygote / secondary zygote 负责普通 App 与 `system_server`;child zygote 分出 WebViewZygote 和 App Zygote,并标出各自独立 socket]

<!-- AIW-源码调研-2026-04-20 -->
**补充：USAP Pool 不服务 Child Zygote 的源码级证据**

android14-release 的 `ZygoteServer.java` 中存在明确的代码级隔离：

```java
// ZygoteServer(boolean isPrimaryZygote) 构造函数
// frameworks/base/core/java/com/android/internal/os/ZygoteServer.java @ android14-release
ZygoteServer(boolean isPrimaryZygote) {
    // ...
    mUsapPoolSupported = true;  // Primary/Secondary 均为 true
}

// 无参构造函数(Child Zygote 使用)
ZygoteServer() {
    mUsapPoolSupported = false;  // Child Zygote 禁用了 USAP Pool
}
```

`mUsapPoolSupported` 字段在 ZygoteServer 构造时即被固定，Child Zygote 的 `ZygoteServer()` 无参构造将 `mUsapPoolSupported` 设为 `false`,导致 poll 循环中 USAP socket 和 pipeFDs 的注册逻辑被完全跳过。源码路径：`frameworks/base/core/java/com/android/internal/os/ZygoteServer.java`,行 95-130。

**USAP Pool 在 AOSP 16 中的默认状态：** 即使在 Primary Zygote 上，USAP Pool 也默认关闭(`mUsapPoolEnabled = false`)。OEM 可以通过 `persist.device_config.activity_manager_native_boot.usap_pool_enabled` 系统属性开启。此外，USAP 明确不支持 App Zygote、WebViewZygote 等 Child Zygote 派生的子孵化器--这些路径必须走传统 fork,不能从 USAP pool 拿现成进程。


## 版本演进里和 Zygote 相关的变化

把版本线收成下面这张表更稳，能避免把 android-16 的 trace 名和能力边界套到老版本上。

| 版本段 | preload / 观测口径 | 进程创建能力边界 | 阅读本章时的默认口径 |
| --- | --- | --- | --- |
| Android 5-7 | 以传统 `preloadClasses()`、资源和共享库预热为主 | 还没有 WebViewZygote、App Zygote、USAP | 先把 Zygote 看成主 zygote + 普通 fork 路径 |
| Android 8 | 增加 WebViewZygote | 仍没有 App Zygote 和 USAP | WebView 相关进程开始脱离主 zygote 单独预热 |
| Android 9 | `PreloadAppProcessHALs` 引入(gralloc mapper HAL 预加载)+ `preloadOpenGL` | WebViewZygote,还没有 USAP | gralloc HAL 库开始在 zygote 期预热 |
| Android 10 | `PreloadGraphicsDriver` + `CacheNonBootClasspathClassLoaders` 引入 | 开始出现 App Zygote 雏形 | GPU 驱动预加载和非启动类路径 ClassLoader 缓存上线 |
| Android 11-15 | USAP pool 成熟，App Zygote / `ZygotePreload` 稳定 | 普通 App 可能命中 USAP;isolated service 可能走 App Zygote | 先分清 primary / secondary 主线和 child zygote 支线 |
| Android 16-17 | 本章以 android-17.0.0_r1 为基准验证，preload 主序列（`PreloadClasses`、`CacheNonBootClasspathClassLoaders`、`PreloadResources`、`PreloadAppProcessHALs`、`PreloadGraphicsDriver`）与 android-16 一致；新增 `HttpEngine.preload()` 可选 | USAP、App Zygote、WebViewZygote 仍然共存 | Perfetto 里按本章验证的 slice 名查询，并把 `launching: <package>` 当作覆盖整段启动的 span |

`DeliQueue` 属于 MessageQueue / Looper 的实现演进，应用侧默认生效的版本边界是 Android 17 / targetSdk 37,不属于本章验证的 Android 16 Zygote 机制本体。本章只在交叉引用里保留这个名词，具体实现和版本差异放到 §1.13 讨论。

## 常见误区

### 误区 1:system_server 和 Zygote 之间走 Binder

不是。Binder 大量出现在 App / Launcher 到 `system_server` 的路径里，但 `system_server` 把建进程请求发给 Zygote 时，实际走的是 zygote socket / LocalSocket。这一点可以对照 `ProcessList.java`、`ZygoteProcess.java` 的代码路径确认。

### 误区 2:`PreloadGraphicsDriver` 等于 App 的 GPU context 已经初始化完

不是。它对应的是图形驱动加载和初始化的预热，不等于每个 App 的 RenderThread、EGL context、Surface、首帧绘制都已经准备好了。后者仍然发生在具体应用进程启动之后。

### 误区 3:冷启动慢，先怀疑 Zygote fork

大多数情况下不该这么想。平台工程里当然会关心 Zygote 和 USAP,但对应用启动分析来说，更常见的瓶颈通常在 `bindApplication`、`ContentProvider`、`Application.onCreate()`、首帧渲染，而不是 fork 本身。

### 误区 4:主 Zygote preload 了所有常用库

不要把 framework preload 和应用侧库 preload 混成一锅。`preloaded-classes` 主要覆盖 framework 高频类，不意味着 AndroidX、三方 SDK、业务类都已经在 Zygote 里热好了。

## 与其他章节的关系

- **§1.2 系统启动全流程**:看 Zygote 在开机链里的位置，以及为什么 preload 会直接影响开机时间。
- **§1.3 进程模型**:看 Binder、LocalSocket、共享内存这些 IPC 机制在 Android 里的职责边界。
- **§8.2 应用启动分析**:看冷启动从 `bindApplication` 到首帧的完整分析路径。
- **§8.3 启动优化策略**:看应用侧如何优化 `Application` 初始化、Provider、首帧和类加载布局。

## 参考资料

- `frameworks/base/core/java/com/android/internal/os/ZygoteInit.java`:preload、zygote 主入口、child zygote 入口
- `frameworks/base/core/java/com/android/internal/os/Zygote.java`:`forkAndSpecialize()`、`specializeAppProcess()`、`PostFork`
- `frameworks/base/core/java/android/os/ZygoteProcess.java`:`startViaZygote()`、`zygoteSendArgsAndGetResult()`、`startChildZygote()`、`preloadApp()`
- `frameworks/base/core/java/com/android/internal/os/RuntimeInit.java`:`applicationInit()`
- `frameworks/base/core/java/android/app/ActivityThread.java`:`attachApplication`、`bindApplication`、`handleBindApplication()`
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java`:`Process.start(...)` 的调用点
- `frameworks/base/services/core/java/com/android/server/am/EventLogTags.logtags`:`am_proc_start` / `am_proc_bound`
- `frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java`:`launching: <package>` trace 名称
- `frameworks/base/core/java/android/os/AppZygote.java`:App Zygote 的 child zygote 用法
- `frameworks/base/core/java/android/webkit/WebViewZygote.java`:WebViewZygote 的 child zygote 用法
- `frameworks/base/config/preloaded-classes`:framework preload 列表
- 官方文档：<https://source.android.com/docs/core/runtime/zygote>
- Android Developers API reference:<https://developer.android.com/reference/android/app/ZygotePreload>
