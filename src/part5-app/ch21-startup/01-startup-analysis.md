---
title: "启动完整路径分析（App 视角）"
chapter: "21.1"
section: "21.1"
status: ready-for-review
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-05-12"
last_verified_against: "AOSP android-15.0.0_r1, Android Developers launch-time docs"
confidence: medium
drafted_date: "2026-05-12"
sources:
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/wm/ActivityMetricsLogger.java"
tags: [cold-start, warm-start, hot-start, ttid, ttfd, startup-trace, perfetto]
related_chapters: ["8.2", "8.3", "1.7", "1.11", "21.2"]
pipeline_stage: task2b_pending
task6_state: reviewed
task9_state: reviewed
task2b_state: pending
task2b_result: pending
reviewed_by: openclaw-task6
reviewed_date: "2026-05-14"
task6_result: pass-light-edit
last_task6_review_log: logs/review/2026-05-14-16-review.md
task9_result: needs-rework
task9_reviewed_by: openclaw-task9
task9_reviewed_date: "2026-05-14"
last_task9_at: "2026-05-14T15:33:00+08:00"
last_task9_review_log: logs/deep-review/2026-05-14-15-deep-review.md
task9_review_notes: "2026-05-14 Task9：needs-rework。P0 1 / P1 2 / P2 0；首帧回调 API 名、TTID 终点近似、SharedPreferences 版本口径仍需回炉。"
---

# 启动完整路径分析（App 视角）

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 冷 / 温 / 热启动在 App 侧的耗时划分
- 🔹 Application.onCreate、Activity.onCreate、首帧渲染各阶段耗时分布
- 🔹 启动耗时的度量方法：TTID / TTFD / 自定义埋点
- 🔹 Perfetto 启动分析实战

### 扩展（可选深入）

- 🔸 启动过程中的 ClassLoader 与 dex 加载开销

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 本节定位

8.2 节从系统层面说明了冷启动的完整流程——从用户点击到首帧绘制的每一步系统行为。本节切换到 App 开发者的视角，回答一个更实际的问题：**拿到一个启动慢的 App，从哪里下手分析？**

两种视角的分工：8.2 节告诉你"每一步在干什么、为什么需要这一步"，本节告诉你"每一步耗时多少、怎么量、怎么从 Perfetto 里读出来"。

## 冷 / 温 / 热启动：App 侧的耗时分布

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

三种启动状态的定义和系统级行为在 8.2 节已经讲过。这里只从 App 侧能看到的时间段来划分。

### 冷启动：App 侧的四个耗时阶段

冷启动在 App 进程内可观测到的路径分为四段：

```
进程启动 → Application 创建 → Activity 创建与布局 → 首帧绘制
```

**阶段 1：进程启动到 Application.attachBaseContext**

[已验证: AOSP android-15.0.0_r1, ActivityThread.java]

Zygote fork 出子进程后，`ActivityThread.main()` 开始执行。这一阶段 App 开发者几乎没有可控的代码介入点——从 fork 到 `attachBaseContext` 之间的耗时完全由系统决定。主要开销在 ART 运行时初始化、主线程 Looper 创建、以及 `attachApplication` 的 Binder 调用。

在 Perfetto 中，这个阶段对应 App 进程从出现到 `ActivityThreadMain` slice 开始之间的一段空白。典型耗时 50-150ms，与设备性能和 `.so` 库数量相关。App 侧无法优化，但可以间接加速：减少不必要的配置项解析和 `loadLibrary` 调用数量。

**阶段 2：Application.attachBaseContext 到 Application.onCreate 结束**

[已验证: AOSP, ActivityThread.handleBindApplication]

这是 App 开发者能直接控制的第一个耗时入口。`attachBaseContext` 和 `onCreate` 之间包含了大部分 SDK 的初始化逻辑。常见耗时大户：

- 第三方 SDK 初始化（Analytics、Push、Crash 上报等）
- 数据库打开与升级检查（Room、SQLiteOpenHelper）
- MultiDex 安装（`MultiDex.install()`，仅 `minSdkVersion < 21` 的场景）
- 全局配置读取（SharedPreferences 读取、远程配置拉取）
- 网络框架预热（OkHttp ConnectionPool 初始化、DNS 预解析）

在一个中大型 App 中，`Application.onCreate` 的耗时通常在 200-800ms 之间，是冷启动优化最常见的切入点。优化策略在 21.2 节展开。

**阶段 3：Activity.onCreate 到 View 树构建完成**

[已验证: AOSP, LaunchActivityItem.java]

`Application.onCreate` 返回后，system_server 通过 `ClientTransaction` 向 App 发送 `LaunchActivityItem`。App 主线程处理这条事务时执行 Activity 生命周期：`onCreate` → `onStart` → `onResume`。

在 `Activity.onCreate` 中，`setContentView` 触发 XML 布局的 inflate——同步的 XML 解析 + View 对象创建过程。复杂布局层级（嵌套超过 10 层、包含大量自定义 View）的 inflate 耗时可能达到 50-200ms。

`onResume` 返回后，`ActivityThread.handleResumeActivity()` 在 `addView` 阶段创建 `ViewRootImpl` 并通过 `setView` 触发后续 traversal 调度。`ViewRootImpl` 构造时注册 `Choreographer` 回调，为主线程接收 VSync 信号做准备。但此时还没有绘制任何像素——第一帧的绘制要等下一个 VSync 到来。

**阶段 4：首帧绘制（First Draw）**

[已验证: AOSP, ViewRootImpl.performTraversals]

下一个 VSync 信号到来时，`Choreographer` 回调触发 `ViewRootImpl.performTraversals()`，执行 `measure` → `layout` → `draw` 三步。使用硬件加速（Android 4.0+ 默认开启）时，draw 阶段生成 `DisplayList` 并交给 `RenderThread` 处理。

`RenderThread` 通过 GPU 执行绘制命令，完成后通过 `queueBuffer()` 将帧提交给 `SurfaceFlinger`。从 `performTraversals` 开始到帧提交完成，典型耗时 10-50ms。

首帧绘制完成的时刻就是 TTID（Time To Initial Display）的终点。从用户视角看，这就是屏幕上第一次出现 App 内容的时刻。

### 冷启动各阶段典型耗时分布

| 阶段 | 起止点 | 典型耗时 | 可控程度 |
|------|--------|----------|----------|
| 进程初始化 | fork → attachBaseContext | 50-150ms | 几乎不可控 |
| Application 初始化 | attachBaseContext → onCreate 结束 | 200-800ms | **高度可控** |
| Activity 创建 | Activity.onCreate → onResume 结束 | 50-200ms | 可控 |
| 首帧绘制 | performTraversals → queueBuffer | 10-50ms | 部分可控 |

> **注意**：以上数据基于中大型 App 在中端设备（如 Snapdragon 778G）上的典型范围。具体数值因 App 复杂度、设备性能、Android 版本差异很大。优化前必须先量自己的数据，不要套用别人的数字。

### 温启动和热启动：App 侧的简化路径

温启动跳过了阶段 1 和阶段 2（进程已存在、Application 已初始化），直接从 Activity 创建开始。App 侧的耗时集中在 `Activity.onCreate` 的布局重建和数据加载上。温启动的典型耗时是冷启动的 40%-60%。

热启动只走 `onRestart` → `onStart` → `onResume`，不创建新的 Activity 对象。如果 Activity 保持了视图状态，`performTraversals` 只需处理 invalidate 标记的区域，耗时通常在 16ms 以内。但如果系统在后台回收了 Bitmap 等资源，热启动可能退化为接近温启动的耗时。

## Application.onCreate、Activity.onCreate、首帧渲染：逐阶段深入

### Application.onCreate：最常被低估的耗时黑洞

Application.onCreate 在主线程同步执行。很多开发者习惯在这里初始化所有 SDK，因为它"只会执行一次"。但这"一次"发生在冷启动的关键路径上。

典型问题模式：

- **串行初始化**：10 个 SDK 各耗时 20-50ms，串行执行就是 200-500ms
- **IO 操作**：`SharedPreferences` 第一次 `getSharedPreferences()` 会触发磁盘 XML 文件读取和解析（`SharedPreferencesImpl#loadFromDisk()`），首次访问可能触发异步加载并在 `awaitLoadedLocked()` 等待结果；大文件仍有 5-20ms 开销
- **数据库操作**：`SQLiteOpenHelper.getReadableDatabase()` 首次调用可能触发 `onCreate` 或 `onUpgrade`，涉及磁盘 IO
- **Class 加载**：某些 SDK 通过反射加载类，首次加载触发 dex 的 class 查找和验证

[结构参考: Clippings/Android 性能优化 - 原理：重新认识应用的速度优化.md]

从 CPU 时间角度看，`Application.onCreate` 中的代码如果全部是 CPU 计算逻辑，那多线程并行可以将总 CPU 时间压缩到最慢的那个任务。但如果包含 IO 操作（数据库、文件、网络），多线程的收益受限于 IO 等待。这也是为什么启动优化通常先做 IO 移除和延迟初始化，再做并行化——先把不该在启动路径上的操作拿走，再对剩下的做并行。

度量 `Application.onCreate` 耗时的方法：

```kotlin
class MyApplication : Application() {
    override fun onCreate() {
        val start = System.nanoTime()
        super.onCreate()
        // ... SDK 初始化 ...
        val elapsed = (System.nanoTime() - start) / 1_000_000.0
        Log.d("Startup", "Application.onCreate: ${"%.1f".format(elapsed)}ms")
    }
}
```

这段代码只能在开发阶段使用。线上监控需要用 `SystemClock.elapsedRealtime()` 记录时间戳，并通过 APM SDK 上报。注意 `System.nanoTime()` 和 `SystemClock.elapsedRealtime()` 的区别：前者用于测量区间耗时，后者可以跨进程对齐时间线。

### Activity.onCreate：布局 inflate 是主要开销

`setContentView(int)` 内部调用 `LayoutInflater.inflate()`，执行 XML 解析和 View 对象创建。每个 View 的创建涉及反射调用（`LayoutInflater.createView()`）和属性解析（`TypedArray`）。

影响 inflate 耗时的因素：

- **布局层级深度**：每增加一层 `ViewGroup`，多一次 `addView` 和 `requestLayout`
- **View 数量**：单屏超过 80 个 View 时 inflate 耗时开始显著增加
- **自定义 View**：自定义 View 的构造函数中如果有复杂初始化（如 `Paint` 对象创建、`Typeface` 加载），会放大 inflate 耗时
- **`include` 和 `ViewStub`**：`include` 在 inflate 时立即展开，`ViewStub` 延迟到 `inflate()` 被调用时才展开

减少 inflate 耗时的策略（详见 22.1 节）：

- 用 `ViewStub` 延迟加载非首屏可见的布局区域
- 用 AsyncLayoutInflater（`androidx.asynclayoutinflater`）在子线程执行 inflate
- 减少层级：用 `ConstraintLayout` 替代多层嵌套的 `LinearLayout` + `RelativeLayout`
- 避免在 View 构造函数中做 IO 操作

### 首帧渲染：从 performTraversals 到帧提交

首帧渲染的 `measure` → `layout` → `draw` 三步在主线程同步执行。`draw` 阶段如果启用了硬件加速（默认），生成 `DisplayList` 后交给 `RenderThread` 异步执行 GPU 命令。

主线程在 `draw` 完成后即可继续处理后续消息，不必等 `RenderThread` 完成。但帧必须等 `RenderThread` 完成 `queueBuffer` 并经 `SurfaceFlinger` 合成后才能显示在屏幕上。

在 Perfetto 中，首帧渲染的观测点：

- 主线程：`performTraversals` slice
- RenderThread：`DrawFrame` slice，结束时间对应帧提交完成
- SurfaceFlinger：对应 `commit` 和 `composite` slice，合成完成即送显

如果首帧渲染超过 16ms（一帧时间），会看到主线程的 `performTraversals` 跨越两个 VSync 边界，这就是掉帧。

## 启动耗时的度量方法：TTID / TTFD / 自定义埋点

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

### TTID（Time To Initial Display）

TTID 度量的是从系统收到 `startActivity` 调用到首帧绘制完成的时间。在 Android 4.4（API 19）+ 上通过 logcat 可以观测：

```
ActivityTaskManager: Displayed com.example/.MainActivity: +1s234ms
```

这个 `+1s234ms` 就是 TTID。系统通过 `ActivityMetricsLogger` 在 `startActivity` 时记录起点，在 `reportDrawFinished` 时记录终点。

TTID 的局限：它只度量到首帧显示，不关心首帧是否有实际内容。如果 `SplashScreen` 显示了一个纯色背景，TTID 会很漂亮，但用户还在等有效内容。

### TTFD（Time To Fully Drawn）

[已验证: 官方文档, developer.android.com/topic/performance/vitals/launch-time]

TTFD 度量的是从 `startActivity` 到 App 声明"内容已完整加载"的时间。App 通过调用 `Activity.reportFullyDrawn()` 告知系统内容加载完毕：

```kotlin
override fun onResume() {
    super.onResume()
    loadData {
        // 数据加载完成，列表渲染完毕
        reportFullyDrawn()
    }
}
```

Android 12（API 31）之前，`reportFullyDrawn()` 会在 logcat 中输出：

```
ActivityTaskManager: Fully drawn com.example/.MainActivity: +2s567ms
```

Android 12+ 引入了 `SplashScreen` API，启动画面的生命周期由首帧绘制、`keepOnScreenCondition` 和退出动画控制——不是由 `reportFullyDrawn()` 直接控制。TTFD 的上报由 `Activity.reportFullyDrawn()` 触发，这是一个独立的诊断/优化度量，不改变 SplashScreen 的显示时机。两个机制可以配合使用：SplashScreen 负责视觉过渡，`reportFullyDrawn()` 负责标记内容完整加载的时间点。

AndroidX `activity:activity:1.7.0+` 提供了 `FullyDrawnReporter`，支持多个组件分别注册完成回调，全部完成后再调用 `reportFullyDrawn()`。这对于需要等待多个异步操作（网络请求 + 本地缓存 + 配置加载）才能展示完整内容的页面更实用。注意 `FullyDrawnReporter` 是 AndroidX 库组件，不是 Android 15 平台 API。

### 度量方法对比

| 方法 | 起点 | 终点 | 获取方式 | 适用场景 |
|------|------|------|----------|----------|
| TTID | startActivity | 首帧绘制 | logcat `Displayed` 行、`adb shell am start -W`、Perfetto | 冷启动基准度量 |
| TTFD | startActivity | reportFullyDrawn | logcat `Fully drawn` 行、Perfetto | 度量内容完整加载耗时 |
| 自定义埋点 | 自定义起点 | 自定义终点 | APM SDK 上报 | 精细化分析特定阶段 |

### 自定义埋点的实践

TTID 和 TTFD 是系统级度量，粒度到 Activity 级别。要精细化分析 App 侧各阶段耗时，需要自己埋点。

推荐的时间记录方式：

```kotlin
object StartupTracer {
    private val marks = mutableMapOf<String, Long>()

    fun mark(name: String) {
        marks[name] = SystemClock.elapsedRealtimeNanos()
    }

    fun duration(from: String, to: String): Long? {
        val start = marks[from] ?: return null
        val end = marks[to] ?: return null
        return (end - start) / 1_000_000 // ms
    }
}
```

建议的埋点位置：

| 埋点名称 | 位置 | 记录时机 |
|----------|------|----------|
| `app_attach` | `Application.attachBaseContext` | 方法第一行 |
| `app_create_start` | `Application.onCreate` | `super.onCreate()` 之前 |
| `app_create_end` | `Application.onCreate` | 方法最后一行 |
| `activity_create_start` | `Activity.onCreate` | `super.onCreate()` 之前 |
| `view_created` | `Activity.onCreate` | `setContentView()` 之后 |
| `activity_resume` | `Activity.onResume` | 方法第一行 |
| `first_frame` | `ViewTreeObserver.registerFrameCommitCallback()` | 帧提交回调 |

`first_frame` 埋点有几种实现方式，观测点各不相同：

- **`ViewTreeObserver.registerFrameCommitCallback()`**：在帧绘制完成后回调，最接近"帧已提交"语义。Android 10+ 可用，只对硬件渲染生效；回调表示帧已提交到 swap chain，不等于已显示。回调是一次性消费语义，如需取消尚未触发的回调，使用 `unregisterFrameCommitCallback(callback)`。
- **`Choreographer.postFrameCallback()` 的首次回调**：回调时 VSync 已到达，`performTraversals` 即将开始或刚开始。观测点在帧绘制前，比 `registerFrameCommitCallback` 早。
- **`Window.OnFrameMetricsAvailableListener`**：Android 7.0+ 提供，可以获取帧的绘制、布局、GPU 处理等分阶段耗时。适合线上监控，不适合做单次首帧标记。
- **`ViewTreeObserver.OnPreDrawListener` / `OnDrawListener`**：分别在 `onPreDraw` 和 `onDraw` 阶段触发。注意 `OnDrawListener` 不能在 `onDraw()` 内调用 `removeOnDrawListener()`，否则会抛 `IllegalStateException`。

选择建议：开发阶段用 `registerFrameCommitCallback()` 做首帧标记最直接；线上监控用 `OnFrameMetricsAvailableListener` 获取完整帧指标。

### 线上监控注意事项

[结构参考: Clippings/Android 性能优化 - 如何才能做好 Android 性能优化？.md]

线上启动监控需要关注几个问题：

- **P90 / P95 / P99 分位**：平均数会被长尾拉高，中位数掩盖慢启动。P90 是最常用的衡量指标
- **分设备分版本统计**：低端设备的冷启动耗时可能是高端设备的 3-5 倍，不区分设备看数据会得出错误的结论
- **冷 / 温 / 热分开统计**：三种启动状态的耗时量级完全不同，混在一起看没有意义
- **首次安装 vs 升级**：首次安装没有 dex2oat profile，启动速度会明显慢于升级用户。Baseline Profile 的效果主要体现在首次安装场景

## Perfetto 启动分析实战

这一节用一次完整的冷启动 Trace 分析，展示从 Perfetto 中提取启动各阶段耗时的方法。

### Trace 抓取

启动分析需要抓取的 atrace categories：

```bash
adb shell perfetto \
  -c - --txt \
  -o /data/misc/perfetto-traces/startup.pb \
<<EOF
buffers: {
    size_kb: 63488
}
data_sources: {
    config {
        name: "linux.ftrace"
        ftrace_config {
            ftrace_events: "sched/sched_switch"
            ftrace_events: "power/cpu_frequency"
            atrace_categories: "am"
            atrace_categories: "view"
            atrace_categories: "dalvik"
            atrace_categories: "sched"
            atrace_categories: "binder_driver"
        }
    }
}
duration_ms: 30000
EOF
```

关键 categories：

- `am`：Activity Manager 相关事件，包含 `BindApplication`、`activityStart`、`activityResume` 等 slice
- `view`：View 系统事件，包含 `performTraversals`、`measure`、`layout`、`draw` 等 slice
- `dalvik`：ART 虚拟机事件，包含 GC、class loading 等 slice
- `sched`：CPU 调度事件，显示线程在哪个 CPU 核上执行
- `binder_driver`：Binder 事务，显示跨进程调用的耗时

抓取启动 Trace 的触发方式：

1. **手动触发**：先开始录制 Trace，然后通过 `adb shell am start` 启动 App
2. **atrace + App 启动**：用 `adb shell am start -W` 配合 Trace 抓取
3. **Perfetto 的事件触发模式**：配置 `trigger_config` 以 `am start` 命令作为触发条件

### 在 Perfetto 中定位冷启动各阶段

打开 Trace 后，按进程筛选目标 App。冷启动的 App 进程会在 Trace 中间位置突然出现（fork 后才有进程）。

**定位进程创建点**：

在 system_server 进程中搜索 `Start proc` 或 `Start process: xxx`，这是 ATMS 决定创建新进程的时间点。

**定位 Application 初始化**：

在 App 进程中搜索以下关键 slice：

- `ActivityThreadMain`：`ActivityThread.main()` 开始执行
- `bindApplication`：系统向 App 发送 bindApplication 消息
- `createApplicationContext`：Application Context 创建
- `Application.onCreate`：如果在 `Application.onCreate` 中手动加了 trace tag，会直接显示；否则通过 `bindApplication` slice 的结束时间估算

**定位 Activity 创建**：

搜索 `activityStart` 或 `activityCreate` slice。如果 App 有多个 Activity，需要确认是目标 Activity 的启动事件。

**定位首帧绘制**：

搜索 `performTraversals` slice。第一次出现的就是首帧的 `measure` → `layout` → `draw`。主线程上的 `Choreographer#doFrame` slice 也可以定位首帧。

在 RenderThread 上搜索 `DrawFrame`，第一次出现对应首帧的 GPU 渲染。

**定位 TTID 终点**：

`performTraversals` 结束只定位了首帧 CPU traversal 的完成。首帧还要经过 RenderThread `DrawFrame`、buffer 提交和 `ViewRootImpl`/`WindowSession` 的 draw-finished 上报。系统侧的 TTID 终点是 `Displayed` 时间，可通过 logcat `ActivityManager: Displayed` 或 `am start -W` 观测。Perfetto 中如无法精确匹配 `reportDrawFinished` / frame commit 相关事件，用 `performTraversals` 结束作为 TTID 下界近似，并标注这是 CPU 侧终点，不含 RenderThread/GPU/提交阶段。

### 常见的启动 Trace 图谱

**典型冷启动的 Perfetto 时间线**（从上到下）：

```
system_server:
  ├── Start proc                         ← 进程创建请求
  └── attachApplication                  ← Binder 调用，通知进程就绪

App 主线程:
  ├── ActivityThreadMain                 ← 进程入口
  ├── bindApplication
  │   ├── attachBaseContext
  │   └── Application.onCreate           ← SDK 初始化（通常最长）
  ├── activityCreate
  │   ├── setContentView (inflate)
  │   └── Activity.onCreate 完成
  ├── activityStart
  ├── activityResume
  │   └── ViewRootImpl 创建
  └── performTraversals                  ← 首帧绘制
      ├── measure
      ├── layout
      └── draw → DisplayList 生成

RenderThread:
  └── DrawFrame                          ← GPU 渲染首帧
      └── queueBuffer()                  ← 帧提交给 SurfaceFlinger
```

### 常见异常模式

**1. Application.onCreate 过长**

在 Perfetto 中表现为 `bindApplication` slice 持续时间超过 500ms。展开 slice 看内部是否有明显的 `GC` 事件（`dalvik` category 下的 `ConcurrentGC` slice）或 `class loading` 事件。

GC 在启动阶段抢占 CPU 是常见问题。ART 的 `HeapTaskDaemon` 线程在 Java 堆达到阈值时触发并发 GC，虽然不 STW，但会抢占 CPU 时间片，导致主线程被调度出去。Android 8+ 系统在启动时自动抑制 GC 2 秒，但 App 侧如果快速分配大量对象（如 SDK 初始化时创建大量配置对象），仍可能提前触发 GC。

[结构参考: Clippings/Android 性能优化 - 如何通过 GC 抑制来提升启动速度？.md]

**2. 布局 inflate 耗时**

在 `activityCreate` slice 内，如果 `setContentView` 到 `Activity.onCreate` 结束之间的耗时超过 100ms，通常可以判定为布局 inflate 问题。用 Android Studio Layout Inspector 检查布局层级，或者用 `LayoutInspector` 命令行工具 dump View 树。

**3. 首帧绘制跨 VSync**

如果 `performTraversals` 持续时间超过 16ms，在 Perfetto 中会看到主线程的 `doFrame` 跨越两个 VSync 边界。这意味着首帧掉帧，用户感知为启动后短暂的白屏或卡顿。

常见原因：布局层级过深导致 `measure`/`layout` 递归开销大，或 `draw` 阶段有复杂的自定义 `onDraw` 逻辑。

### SQL 查询：批量分析启动耗时

Perfetto 的 SQL 模式可以批量分析多次启动的耗时分布。以下查询提取冷启动的各阶段耗时：

```sql
-- 提取 Application 初始化耗时
SELECT
  s.name as slice_name,
  s.dur / 1e6 as dur_ms
FROM slice s
JOIN thread_track tt ON s.track_id = tt.id
JOIN thread t ON tt.utid = t.utid
JOIN process p ON t.upid = p.upid
WHERE p.name = 'com.example.app'
  AND s.name IN (
    'bindApplication',
    'activityCreate',
    'performTraversals'
  )
ORDER BY s.ts;
```

```sql
-- 提取主线程在冷启动期间的 CPU 运行状态分布
SELECT
  state,
  sum(dur) / 1e6 as total_ms
FROM thread_state
WHERE utid = (
  SELECT t.utid FROM thread t
  JOIN process p ON t.upid = p.upid
  WHERE t.name = 'main' AND p.name = 'com.example.app'
)
AND ts BETWEEN (
  SELECT s.ts FROM slice s
  JOIN thread_track tt ON s.track_id = tt.id
  JOIN thread t ON tt.utid = t.utid
  JOIN process p ON t.upid = p.upid
  WHERE s.name = 'bindApplication' AND p.name = 'com.example.app'
  LIMIT 1
)
AND (
  SELECT s.ts + s.dur FROM slice s
  JOIN thread_track tt ON s.track_id = tt.id
  JOIN thread t ON tt.utid = t.utid
  JOIN process p ON t.upid = p.upid
  WHERE s.name = 'performTraversals' AND p.name = 'com.example.app'
  LIMIT 1
)
GROUP BY state;
```

这段查询帮助判断主线程在启动期间是"在跑"还是"在等"——如果 `Runnable` 状态占比低于 70%，说明主线程被频繁调度出去，可能的原因包括 GC 抢占、Binder 调用等待、锁竞争。

## 扩展：启动过程中的 ClassLoader 与 dex 加载开销

[已验证: AOSP, ART runtime class linking]

### Class 加载在启动中的位置

Android 的类加载在首次使用时触发（lazy loading）。`Application.onCreate` 中引用到的每个类，在首次访问时需要经历：

1. **Dex 文件定位**：`DexPathList` 在 dex 数组中查找类的定义
2. **Class 数据读取**：从 dex 文件中读取类的数据结构
3. **类验证与链接**：`ClassLinker::VerifyClass`，检查类的合法性
4. **类初始化**：执行 `<clinit>` 静态初始化块

在冷启动中，类加载的开销主要集中在 `Application.onCreate` 阶段——大量 SDK 的初始化代码引用了之前从未加载过的类。

### 类重排（Dex Reorder）对启动的影响

[结构参考: Clippings/Android 性能优化 - 缓存优化：冷热端分离+重排序，提升缓存命中率.md]

ART 在加载 dex 中的类时，如果类的定义在 dex 文件中分布过于分散，会导致 CPU cache 命中率降低。通过将启动阶段需要加载的类集中排列在 dex 文件的前部，可以提升 L1/L2 cache 的命中率。

这是局部性原理的直接应用：相邻的类定义在加载时会被一起读入 cache line。Android 的 Dex Layout 优化工具（`profman` + dex layout 优化）和 Baseline Profile 机制都在做这件事。

Baseline Profile 通过在安装时指定 AOT 编译的类和方法列表，让这些类在启动前已经被编译成机器码，跳过了运行时的 dex 解释和 JIT 编译。这比 dex 重排更进一步——不仅减少了类查找开销，还消除了首次执行时的解释开销。

Baseline Profile 的制作和使用在 21.4 节详细介绍。从 dex 加载角度看，Baseline Profile 的收益取决于 App 在启动路径上引用了多少未编译的类——对于未使用任何 AOT 编译的 App，收益可能达到 20%-40%；对于已经使用过 dex2oat 编译的 App，收益主要来自更精准的热点方法选择。

### 如何观测类加载耗时

在 Perfetto 的 `dalvik` category 中能看到类加载事件。但 Perfetto 默认不记录每次类加载的详细信息——需要开启 `art::ClassLinker` 的 trace 点。

一种替代方案是使用 `Debug.startMethodTracingSampling()` 在启动阶段做采样 profiling，然后分析采样结果中 `ClassLoader.loadClass` 的出现频率。高频出现说明类加载是瓶颈。

更轻量的方式：在 `Application.attachBaseContext` 中记录时间戳，在 `Application.onCreate` 中分 SDK 记录时间戳，看哪些 SDK 初始化耗时异常长。如果某个 SDK 初始化耗时远超其文档声称的时间，类加载（首次引用 + 依赖类的级联加载）可能是隐藏的原因。
