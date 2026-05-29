---
title: 内存分析工具
chapter: '14.3'
section: '14.3'
status: ready-for-review
reviewed_date: "2026-05-30"
reviewed_by: "openclaw-task6"
drafted_date: '2026-04-03'
drafted_by: openclaw-task2a
applicable_versions: Android 8 (API 26) - Android 17 (API 37)
last_verified: '2026-05-30'
last_verified_against: AOSP android-16.0.0_r1 + Perfetto native-heap-profiler docs + Android Developers memory docs
confidence: high
sources:
- type: blog
  path: https://www.androidperformance.com/2015/04/11/AndroidMemory-Usage-Of-MAT/
- type: blog
  path: https://www.androidperformance.com/2015/04/11/AndroidMemory-Usage-Of-MAT-Pro/
- type: blog
  path: https://www.androidperformance.com/2015/04/11/AndroidMemory-Open-Bitmap-Object-In-MAT/
- type: official
  path: https://developer.android.com/studio/profile/memory-profiler
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: https://developer.android.com/ndk/guides/sanitizers
- type: aosp
  path: system/memory/libmeminfo
- type: aosp
  path: bionic/libc/malloc_debug
tags:
- mat
- leakcanary
- heapprofd
- meminfo
- showmap
- procrank
- memory-tools
related_chapters:
- '10.1'
- '10.2'
- '10.3'
- '14.1'
- '13.1'
pipeline_stage: task9_pending
task6_state: reviewed
task6_result: pass-light-edit
task9_state: pending
task2b_state: fixed
task9_result: auto-fixed
task2b_result: fixed-lite
task2b_rework_date: '2026-05-01'
task2b_fixed_at: '2026-05-28'
task2b_lite_fixed_at: '2026-05-28T15:38:00+08:00'
last_task2b_verifier_at: '2026-05-28T15:47:00+08:00'
task9_reviewed_date: "2026-05-30"
task9_reviewed_by: openclaw-task9
last_task9_at: "2026-05-30T00:28:17+08:00"
task9_review_notes: "2026-05-28 Task9 deep-review: auto-fixed。修正 LeakCanary manualInstall 自动安装关闭方式、MTE ASYNC 崩溃语义和默认启用边界；回到 Task6 复审。 | 2026-05-29 05 Task9 deep-review: auto-fixed。P0 1 / P1 0 / P2 0；修正 LMKD 选杀口径，不再写成由 PSS 总量直接决定，回到 Task6 复审。 | 2026-05-30 Task9 deep-review: auto-fixed。P0 1 / P1 0 / P2 0；修正不存在的 android-17.0.0_r1 验证锚点、malloc_debug AOSP 路径和 libmeminfo main 链接，回到 Task6 复审。"
last_task2b_lite_at: '2026-05-28T15:38:00+08:00'
last_task6_at: "2026-05-30T01:05:00+08:00"
task6_reviewed_date: "2026-05-30"
task6_reviewed_by: "openclaw-task6"
last_task6_review_log: logs/review/2026-05-30-01-review.md
task6_review_notes: "2026-05-30 01: Task6 revisiting review: pass-light-edit；outline 5/5 覆盖；无新增 L1/L2 小修，无新增 L3/L4 回炉项，送 Task9 复审。"
last_task9_autofix_at: "2026-05-30"
last_task9_review_log: logs/deep-review/2026-05-30-00-deep-review.md
reviewed_at: "2026-05-30T01:05:00+08:00"
task9_reviewed_at: "2026-05-29T05:20:00+08:00"
updated_by: "openclaw-task9"
updated_date: "2026-05-29"
task6_l1_l2_fixes: 0
task6_l3_l4_issues: 0
task6_new_rework: false
review_type: "task6-writing-quality-review"
---

# 内存分析工具

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 LeakCanary 原理与配置
- 🔹 MAT（Memory Analyzer Tool）的使用方法
- 🔹 heapprofd（Perfetto）Native 内存分析
- 🔹 adb shell dumpsys meminfo 的详细解读
- 🔹 showmap / procrank / libmeminfo 等内存查看工具

### 扩展（可选深入）

- 🔸 malloc debug / malloc hooks 的使用方法
- 🔸 HWASAN / MTE 用于内存错误检测

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么需要这么多种内存分析工具

做过 Android 内存优化的工程师大概都有这样的体会：内存问题的排查路径特别长，而且每种问题的"入口"不一样。有时候用户反馈"应用越用越卡"，打开 Perfetto 一看，GC 事件密集得像心电图——这可能是 Java 堆泄漏。有时候 Crashlytics 报了一堆 Native crash，信号是 SIGSEGV——这可能是 Native 内存越界访问。还有时候系统日志里 LMK 频繁杀后台，但我们不清楚是哪个进程吃掉了内存。

没有哪一个工具能覆盖所有场景。`LeakCanary` 擅长自动发现 Activity/Fragment 级别的 Java 泄漏，但它对 Native 堆和系统级内存占用无能为力。`MAT` 可以深入分析 hprof 文件中的引用链，找出"谁持有了不该持有的引用"，但它需要你先抓到堆转储，而且是离线分析。`heapprofd` 能实时采样 Native 堆的分配行为，但它给出的不是"谁泄漏了"，而是"谁在分配"。`dumpsys meminfo` 则是全局视角的入口——告诉你这个进程总共占了多少内存、各分多少，但它不会告诉你为什么。

所以我们把这几类工具放在一起讲，目的是帮读者建立一条从"发现内存异常"到"定位根因"的完整排查路径。

## LeakCanary：Java 内存泄漏的自动哨兵

### LeakCanary 解决什么问题

在所有内存分析工具中，LeakCanary 的定位最明确：它是一个开发阶段的自动泄漏检测器。我们不需要手动抓堆转储、不需要打开 MAT 分析引用链——LeakCanary 会在 Activity、Fragment、ViewModel、Service 等组件被销毁后，自动检查它们是否还被 GC 回收。如果没有被回收，它会抓取堆转储、分析引用链，并通过系统通知把泄漏路径展示给开发者。

这个工具的核心定位是"泄漏的早期发现"。很多内存泄漏在开发阶段通常不会触发 OOM——设备内存够大，测试时间不够长。但 LeakCanary 能在泄漏还很小的时候就抓住它，让开发者在代码提交前就修复问题，而不是等到线上用户反馈"应用卡死了"才去排查。

### 工作原理

LeakCanary 的检测流程可以概括为四个步骤。

第一步，**监听生命周期**。LeakCanary 通过注册 `ActivityLifecycleCallbacks` 和 `FragmentLifecycleCallbacks` 来监听 Activity 和 Fragment 的创建与销毁。对于 ViewModel，它利用了 `ViewModel.onCleared()` 回调。当组件被销毁时，LeakCanary 把它包装成一个 `KeyedWeakReference`，并把引用关联到一个 `ReferenceQueue`。

第二步，**触发 GC 后检查可达性**。组件销毁后，LeakCanary 不会立即判断泄漏。它会等待一段时间（默认 5 秒），然后调用 `Runtime.gc()` 尝试触发垃圾回收。之后检查 `ReferenceQueue`——如果 `WeakReference` 被回收了，它应该出现在队列中。如果没出现，说明这个对象仍然被强引用持有，也就是疑似泄漏。

第三步，**堆转储与引用链分析**。确认疑似泄漏后，LeakCanary 调用 `Debug.dumpHprofData()` 抓取 Java 堆转储，然后使用自研的 Shark 库（不是 MAT）解析 hprof 文件，找出从 GC Root 到泄漏对象的最短引用链。

第四步，**通知与展示**。分析完成后，LeakCanary 发送系统通知，点击后会展示完整的泄漏路径。每条泄漏路径会生成一个"泄漏签名"（leak signature），相同签名的泄漏会被归类，避免重复报告。

### 集成与配置

LeakCanary 2.x 的集成非常简单，在 `build.gradle` 中添加一行依赖即可：

```groovy
dependencies {
    debugImplementation 'com.squareup.leakcanary:leakcanary-android:2.14'
}
```

只需要加在 `debugImplementation` 中——LeakCanary 是纯开发工具，绝不应该打包到 release 版本中。添加依赖后不需要任何初始化代码，LeakCanary 会通过 `ContentProvider` 自动完成初始化。

如果需要自定义配置，需要区分两个配置入口：

**堆转储与分析策略**（`LeakCanary.config`）：

```kotlin
LeakCanary.config = LeakCanary.config.copy(
    dumpHeap = true,                    // 是否自动 dump hprof
    objectInspectors = ObjectInspectors.appDefaults  // 引用链分析策略
)
```

**观察等待时间**（`AppWatcher.manualInstall`）：

`retainedDelayMillis`（组件销毁后等待多久再检查可达性）不在 `LeakCanary.Config` 上，需要通过 `AppWatcher` 的手动安装路径配置。使用前先关闭自动安装，官方入口是覆盖 `leak_canary_watcher_auto_install` 资源；也可以直接依赖 `leakcanary-android-core`，避开带自动安装器的 artifact。

```xml
<!-- res/values/leak_canary.xml -->
<resources>
    <bool name="leak_canary_watcher_auto_install">false</bool>
</resources>
```

```kotlin
// Application.onCreate(): 手动安装并自定义等待时间
AppWatcher.manualInstall(
    application = this,
    retainedDelayMillis = 5000  // 默认 5000ms，可按需调整
)
```

如果不需要修改 `retainedDelayMillis`，保持默认自动安装即可，不需要写任何配置代码。

LeakCanary 2.x 还增强了对 Kotlin Coroutines 和 Jetpack Compose 的支持。对于 Coroutines，如果协程泄漏持有了 Activity 引用，LeakCanary 可以在引用链中标注出协程的挂起点。对于 Compose，它能够检测 Composable 函数中意外持有的长生命周期引用。

### 在 Perfetto 中的关联表现

虽然 LeakCanary 本身不依赖 Perfetto，但当 LeakCanary 在检测泄漏过程中调用 `Debug.dumpHprofData()` 时，这一动作在 Perfetto Trace 中会留下明显的痕迹：主线程会出现一个耗时较长的 slice（通常几百毫秒到数秒），标注为 `dumpHprof`。如果在 Trace 中看到周期性的 `dumpHprof` slice，说明 LeakCanary 正在频繁检测到泄漏并抓取堆转储——这时候就应该去看看 LeakCanary 的通知了。

[已验证: 官方文档, https://square.github.io/leakcanary/]
[来源: obsidian/性能优化日报/2026-03-15-LeakCanary-内存泄漏检测.md]

## MAT：Java 堆的深度剖析

### MAT 解决什么问题

MAT（Memory Analyzer Tool）解决的是一个更深入的问题：你已经知道内存有问题了（可能通过 LeakCanary 发现了泄漏，可能通过 `dumpsys meminfo` 看到 Java Heap 持续增长，也可能应用刚发生了 OOM），现在需要搞清楚"到底是谁在占用内存、为什么没有被释放"。

如果说 LeakCanary 是自动化的哨兵，那 MAT 就是手动的解剖刀。它不自动运行，不给你发通知，但当我们把一个 hprof 文件交给它时，它能精确地展示堆中每个对象的持有关系、占用大小、引用路径。高爷有一篇 MAT 三部曲系列文章（入门、进阶、打开 Bitmap 原图），详细介绍了 MAT 的实战用法。

### 抓取 hprof 文件

MAT 分析的输入是 Java 堆转储文件（.hprof）。在 Android 上有几种方式获取这个文件。

最直接的方式是通过 Android Studio。在 Memory Profiler 中，点击 "Dump Java Heap" 按钮（内存面板左上角的下载图标），即可抓取当前应用的 Java 堆。抓取后，Android Studio 会自动将 Dalvik 格式的 hprof 转换为标准 Java hprof 格式。

> **推荐操作**：在抓取堆转储之前，先点击 Memory Profiler 中的"Initiate GC"按钮手动触发一次 GC。这样抓到的 hprof 文件中就不包含 Unreachable 对象——那些已经可以被 GC 回收但还没有被回收的对象。如果不先触发 GC，Unreachable 对象会干扰分析，让你在大量"将被回收"的对象中寻找泄漏对象。

也可以通过命令行抓取：

```bash
# 请求系统在 dump 前先做一次 GC（可选）
adb shell am dumpheap -g --user 0 <pid> /data/local/tmp/heap.hprof

# 不带 -g 时直接抓取当前 Java 堆
adb shell am dumpheap --user 0 <pid> /data/local/tmp/heap.hprof
```

如果要在应用代码里控制抓取时机，可以调用 `Runtime.getRuntime().gc()` 或 `Debug.dumpHprofData()`。这里的 GC 只是 hint，不能把它当成“先回收完再 dump”的严格保证。

抓取后需要转换格式：

```bash
hprof-conv /data/local/tmp/heap.hprof heap-std.hprof
```

### MAT 的核心分析视图

打开 hprof 文件后，MAT 会自动生成一个概览报告（Leak Suspects Report），列出它怀疑有泄漏的对象。但通常我们需要更细致的手动分析。MAT 中最常用的视图有三个。

**Histogram（直方图视图）**：按类名分组统计对象数量和占用内存。这个视图最适合用来回答"哪种类型的对象最多"这个问题。在排查内存泄漏时，我们可以对比两次 hprof（操作前和操作后）的 Histogram，找到数量异常增长的对象类型。

**Dominator Tree（支配者树）**：按对象实例的 retained size（保留大小）排序。Retained size 的含义是"如果这个对象被 GC 回收，总共能释放多少内存"。Dominator Tree 能直接回答"哪个对象占的内存最多"。一个对象支配另一个对象，意味着所有到被支配对象的引用路径都必须经过支配者——所以释放支配者就能释放它支配的所有对象。

**Thread Overview（线程概览）**：展示每个线程的栈帧和持有的对象引用。这个视图在排查"某个内部类或 Handler 持有 Activity 引用"这类泄漏时特别有用，因为你可以直接看到哪个线程持有了泄漏对象。

### 实战分析方法

一个典型的 MAT 分析流程如下。

在 Histogram 视图中，使用正则表达式过滤出我们关心的类。比如我们在 LeakCanary 中看到了某个 Activity 泄漏，就在 Histogram 中搜索这个 Activity 类名。找到后，右键选择 "List objects → with incoming references"（列出持有该对象引用的其他对象）。

然后，沿着引用链逐层展开。MAT 会在引用路径上标记 "Shallow Heap"（对象自身大小）和 "Retained Heap"（该对象被回收后可释放的总大小）。如果某个中间节点的 Retained Heap 异常大，它很可能就是泄漏的关键持有者。

引用链的最末端是 GC Root。GC Root 是 JVM 垃圾回收的起点，通常是静态变量、活跃线程的局部变量、JNI Global Reference 等。如果引用链从一个 GC Root 连到了一个本该被销毁的 Activity，那这条链上的某个引用就是泄漏点。

对于 Bitmap 相关的问题，要先看 Android 版本边界。Android 7.x 及以下，Bitmap 像素数据还在 Java 堆里，MAT 能直接看到 `mBuffer` 一类字段；Android 8.0+ 把像素数据移到了 Native Heap，Java 对象里通常只剩 `mNativePtr`。这时标准 hprof 里拿不到像素内容，MAT 也不能再把 Bitmap 直接还原成图片。现代设备上如果要确认“是哪张图在占内存”，优先用 Android Studio Memory Profiler 看 Bitmap 预览，再结合 `dumpsys meminfo` 的 `Graphics` / `Native Heap`、heapprofd 和图形内存排查路径定位。

### MAT 与 Android Studio Profiler 的关系

Android Studio 自带的 Memory Profiler 也能分析 hprof 文件，提供了可视化的堆浏览和引用链追踪功能。对于大多数日常的内存分析场景，Memory Profiler 已经足够。但 MAT 的优势在于更强大的 OQL（Object Query Language）查询能力和更成熟的引用链分析算法。如果 Memory Profiler 的分析结果不够清晰，或者需要批量查询某个模式的对象，MAT 仍然是更好的选择。

[已验证: 官方文档, https://developer.android.com/studio/profile/memory-profiler]
[来源: obsidian/Personal-Knowlodge/source/AndroidMemory-Usage-Of-MAT.md]
[来源: obsidian/Personal-Knowlodge/source/AndroidMemory-Usage-Of-MAT-Pro.md]
[来源: obsidian/Personal-Knowlodge/source/AndroidMemory-Open-Bitmap-Object-In-MAT.md]

## heapprofd：Native 堆的实时采样分析

### heapprofd 解决什么问题

前面两个工具（LeakCanary 和 MAT）处理的是 Java/Kotlin 堆的内存问题。但 Android 应用的内存不止 Java 堆——Native 堆（通过 `malloc`/`new` 分配的 C/C++ 内存）、Graphic Buffer、共享库的 mmap 区域等，都可能成为内存问题的来源。特别是使用 JNI、游戏引擎、音视频库的应用，Native 堆的占比往往超过 Java 堆。

heapprofd 是 Perfetto 内置的 Native 堆采样分析器。它的工作方式不是抓一次完整的堆转储，而是在运行过程中持续采样内存分配行为。这种方式的开销很低（通常不超过 2%），适合在真实场景中长时间采集。

### 工作机制

heapprofd 的基本思路是"采样分配调用栈"。当被监控的进程调用 `malloc` 时，heapprofd 按照可配置的采样间隔（默认 4096 字节）选择性地记录这次分配。对于被选中的分配，它会捕获完整的调用栈，并记录分配的地址和大小。当这块内存被 `free` 时，heapprofd 也会记录释放事件。

这样在采集结束后，heapprofd 就能告诉你：哪些调用栈路径分配了最多内存、哪些分配没有被释放（可能是泄漏）、内存分配的时间趋势是什么。

heapprofd 盯的是 `malloc` / `free` 一类分配；Graphic Buffer、`dma-buf`、Surface buffer 这类图形内存通常不走这条路，所以它看不到。

heapprofd 支持 Native 分配和 Java 分配两种模式。Native 分配模式从 Android 10 开始支持，监控 `malloc`/`free` 调用。Java 分配模式从 Android 12 开始支持，监控 ART 虚拟机的对象分配。但需要注意，Java 模式展示的是分配的调用栈，而不是对象之间的引用关系——它无法替代 MAT 的引用链分析。

### 使用方法

**方式一：通过 Perfetto UI 配置**

打开 ui.perfetto.dev，在 Trace Config 中勾选 "Heap profiling" 选项，填入目标进程名（如 `com.example.myapp`），然后点击 "Start Recording" 开始采集。这种方式适合有 USB 连接的开发场景。

**方式二：通过命令行**

Perfetto 官方推荐使用 `heap_profile` 脚本（位于 Perfetto 仓库 `tools/` 目录）启动 native heap profiling：

```bash
# 使用 Perfetto 的 heap_profile 工具启动采样
# 脚本会自动配置 heapprofd 数据源并拉取结果
tools/heap_profile -n com.example.myapp
```

`heap_profile` 封装了 heapprofd daemon 的启停和 trace 结果拉取。`heapprofd` 本身是系统级 daemon / Perfetto 数据源，不是面向开发者的稳定 adb shell 入口，不建议直接调用。

**方式三：通过 Perfetto 配置文件**

创建一个 Perfetto 配置文件，指定 heap profiling 数据源：

```protobuf
buffers: {
    size_kb: 65536
}
data_sources: {
    config {
        name: "android.heapprofd"
        heapprofd_config {
            process_cmdline: "com.example.myapp"
            sampling_interval_bytes: 4096
            continuous_dump_config {
                dump_interval_ms: 10000    // 每10秒自动 dump 一次快照
            }
        }
    }
}
```

然后用 `adb shell perfetto --txt -c config.pbtx -o /data/misc/perfetto-traces/trace` 启动采集。注意 `--txt` 参数是必需的——Perfetto CLI 默认按二进制 TraceConfig 解析配置文件，文本格式的 `.pbtxt` 必须显式声明。

### 分析结果

采集完成后，在 Perfetto UI 中打开 trace 文件。在左侧的 Track 列表中会看到 "Heap profiles" 相关的 Track，展开后会出现时间轴上的一系列堆快照（每个快照对应一个时间点的内存分配状态）。

点击某个快照，Perfetto 会展示火焰图（Flamegraph）形式的分配调用栈。火焰图中每个色块的宽度代表该调用栈路径分配的内存大小。最宽的色块就是分配最多的调用路径。

在火焰图的上方，有一个过滤器可以选择查看模式：

- **Total allocations（累计分配）**：展示从采集开始到该时间点的所有分配，包括已释放的。适合查看"哪里在频繁分配"。
- **Allocated at snapshot（当前存活）**：只展示到该时间点仍未被释放的分配。适合查找泄漏——如果某个调用栈的"当前存活"持续增长，大概率是泄漏。

### 前置条件与限制

- 目标设备需要运行 Android 10+。
- 在 userdebug/eng 版本上可以直接使用。在 user 版本上，目标应用需要在 Manifest 中声明 `android:debuggable="true"`，或在 `<application>` 下加入 `<profileable android:shell="true" />`。
- `profileable` 元素从 Android 10 开始可用，允许 shell、Perfetto、simpleperf 在不开启 debug 模式的前提下采集数据。做 release 版本性能分析时，通常优先选 `<profileable android:shell="true" />`。
- 采样模式意味着 heapprofd 不会记录每一次分配。对于小对象的泄漏，可能因为采样间隔而没有被捕获。

[已验证: 官方文档, https://perfetto.dev/docs/data-sources/native-heap-profiler]
[已验证: 官方文档, https://developer.android.com/topic/performance/memory]

## dumpsys meminfo：内存的全局快照

### dumpsys meminfo 解决什么问题

`dumpsys meminfo` 不分析引用链，不抓取堆转储，也不展示调用栈。它做的事情更简单也更基础：给我们一个进程的内存使用概览，告诉你这个进程总共占了多少内存，分别花在了哪里。

这个命令在性能优化的日常工作中有两个主要用途。第一，快速判断"内存是否正常"。如果某个应用的 PSS（Proportional Set Size）明显高于同类型应用，或者 Java Heap 接近了 `dalvik.vm.heapsize` 上限，那内存可能有问题。第二，周期性地执行这个命令，可以观察到内存的长期趋势——如果 PSS 持续增长且不回落，几乎可以确定存在泄漏。

### 输出结构详解

执行 `adb shell dumpsys meminfo <package_name>` 后，输出分为几个主要区域。

**内存分类汇总表**是输出的核心部分。它按照内存类型（Java Heap、Native Heap、Code、Stack、Graphics 等）和内存属性（Private Dirty、Private Clean、Shared Dirty、Shared Clean、Swap）两个维度交叉展示。下面是关键字段的含义。

**PSS（Proportional Set Size）**：这是最核心的指标。PSS 将共享内存按引用进程数均分——如果一个 4KB 的内存页被两个进程映射，那每个进程的 PSS 只算 2KB。PSS 的好处是可以把所有进程的 PSS 加起来，得到系统实际使用的物理内存总量。`dumpsys meminfo` 输出末尾的 `TOTAL PSS` 就是这个进程对系统内存的"真实贡献"。

**USS（Unique Set Size）**：只属于这个进程的私有内存。如果一个进程被杀掉，USS 会被完全释放。USS 是判断"杀掉这个进程能回收多少内存"的直接指标。

**Private Dirty**：被进程修改过的私有内存页。这部分内存不能被系统直接回收（因为内容是脏的），只有杀掉进程才能释放。Private Dirty 通常是 Java Heap 和 Native Heap 的活跃部分，是内存优化中最需要关注的指标。

**Private Clean**：未被修改的私有内存页，通常是代码段（mmap 的 .so、.dex 文件）。这些内存可以在内存紧张时被回收，因为内容可以从文件重新加载。

在分类项中，`Java Heap` 对应 ART 虚拟机管理的 Java/Kotlin 对象堆，`Native Heap` 对应 C/C++ 通过 `malloc` 分配的内存，`Code` 包含 dex 代码和 so 库的内存映射，`Graphics` 主要是 GPU 相关的 Graphic Buffer。`Graphics` 占比异常高时，优先检查 Bitmap、Surface、WebView、视频 buffer 的生命周期；这类问题通常要配合 `showmap`、SurfaceFlinger 和 Perfetto 看，不要直接按 heapprofd 的 Native Heap 路线处理。

**App Summary 区域**在分类汇总表之后，用更简洁的方式总结了几个关键数字：

```text
App Summary
                       Pss(KB)        Rss(KB)
           ----        ------        ------
       Java Heap:     34520         34520
     Native Heap:     12800         12800
            Code:     18920         24600
           Stack:       504           504
        Graphics:     65536         65536
   Private Other:      2400          2400
          System:      8760         10240
           TOTAL:    143440        151064    TOTAL SWAP (KB):        0
```

其中 `TOTAL` 就是这个进程的 PSS 总量。在性能分析中，我们通常关注这个总量的变化趋势，以及 Java Heap + Native Heap 的占比是否合理。

### 实用技巧

**对比前后快照**：在执行某个操作前后各跑一次 `dumpsys meminfo`，然后对比关键指标的变化。比如进入一个页面再退出，如果 PSS 增长了但没有回落，说明这个页面可能有泄漏或内存未释放。

**关注 TOTAL PSS 和 Private Dirty**：PSS 是最全面的指标，Private Dirty 是最"顽固"的指标。如果 Private Dirty 持续增长，问题通常比较严重。

**用 `-d` 参数获取更详细的信息**：`adb shell dumpsys meminfo -d <package>` 会额外输出 Dalvik/ART 的详细内存统计，包括线性分配器（LinearAlloc）和代码缓存的占用情况。

**内存分级与 LMK 的关系**：`dumpsys meminfo` 的 PSS 能评估应用对系统内存压力的贡献，但不要把它理解成 LMKD 的唯一选杀输入。现代 userspace `lmkd` 先根据 PSI / vmpressure、swap 利用率、thrashing 等信号判断是否需要杀进程，再按 `oom_score_adj` 和设备策略选择候选；启用 `ro.lmk.kill_heaviest_task` 时才会倾向选择符合条件的重内存进程。了解应用的 PSS 水平可以评估低内存风险，但归因时还要回到 `oom_score_adj`、LMKD 日志、PSI 和进程 RSS / swap 线索。

[已验证: 官方文档, https://developer.android.com/studio/command-line/dumpsys#meminfo]
[适用版本: Android 8 (API 26) - Android 16 (API 36)]

## showmap / procrank / libmeminfo：命令行内存查看工具集

### 为什么还需要这些工具

`dumpsys meminfo` 提供了应用级别的内存概览，但有时候我们需要更底层的信息。比如，"这个进程的虚拟地址空间是怎么布局的"，"系统上所有进程的内存占用排名是怎样的"，"某个共享库在各进程中的映射情况如何"。这些需求就轮到 `showmap`、`procrank` 和 `libmeminfo` 出场了。

### showmap：进程地址空间的逐行展示

`showmap` 的作用是把 `/proc/<pid>/smaps` 的信息以一种更可读的方式展示出来。它列出了进程中每一个内存映射区域的详细信息：起始地址、大小、PSS、RSS、共享/私有、干净/脏页等。

```bash
adb shell showmap <pid>
```

输出按内存区域分组，每一行对应一个 VMA（Virtual Memory Area）。常见的区域包括：

- `[anon:libc_malloc]`：Native 堆，通过 malloc 分配的匿名内存。如果这个区域异常大，说明 Native 代码在大量分配内存。
- `*.art` / `*.oat`：ART 运行时的 boot image 和编译后的代码。这部分在所有应用进程中共享（通过 Zygote fork），PSS 较低。
- `*.so`（如 `/system/lib64/libc.so`）：共享库的代码段和数据段。代码段通常是 Shared Clean（可以回收），数据段如果有修改就是 Shared Dirty。
- `*.dex` / `*.apk`：应用代码和资源的 mmap 映射。
- `/dev/` 开头的设备映射：通常包括 GPU 的 Graphic Buffer（`/dev/dmabuf` 相关）和其他硬件设备的内存映射。

showmap 最常用的场景是确认"某类内存到底有多大"。当 `dumpsys meminfo` 显示 Native Heap 过大时，可以用 showmap 进一步确认是 `[anon:libc_malloc]` 区域过大还是其他匿名映射（如 mmap 的临时文件）导致的。

`showmap` 需要 root 权限才能查看其他进程的信息。

### procrank：全系统进程内存排名

`procrank` 会列出系统上所有进程的 VSS、RSS、PSS、USS，并按 PSS 排序，适合快速判断"谁在吃内存"。

```bash
adb shell procrank
```

输出示例：

```text
  PID      Vss      Rss      Pss      Uss  cmdline
 1234  2048576  185432   43210   38760  com.example.myapp
 5678  1536000  120432   38900   34560  com.android.systemui
  ...
```

procrank 在排查系统级内存压力时特别有用。当我们需要评估"低内存场景下系统会先杀谁"，或者"多个应用同时运行时内存是否够用"，procrank 提供的跨进程对比视角是 `dumpsys meminfo`（单进程视角）无法替代的。

procrank 的可用性取决于设备。有些厂商的 ROM 没有预装 procrank，需要自己编译推入设备。它的底层依赖 `libpagemap.so`，通过读取 `/proc/<pid>/pagemap` 来获取精确的页面级统计。

### libmeminfo：内存信息的底层库

`libmeminfo` 不是一个直接面向用户的命令行工具，而是 Android 系统内部用于收集内存信息的 C++ 库。它的源码位于 `system/memory/libmeminfo/`（Android 11 起；更早版本在 `system/core/libmeminfo/`）。

libmeminfo 提供了以下能力：

- 读取 `/proc/<pid>/smaps` 并解析为结构化的内存区域信息
- 读取 `/proc/<pid>/pagemap` 获取页面级别的映射详情
- 通过 `/proc/<pid>/clear_refs` 重置进程的工作集（Working Set），用于测量一段时间内的内存增量

`dumpsys meminfo` 和 `procrank` 底层都调用了 libmeminfo 的接口。Java 层的 `android.os.Debug.MemoryInfo` 和 `ActivityManager.MemoryInfo` 也通过 JNI 调用 libmeminfo 获取数据。

对于性能优化工程师来说，了解 libmeminfo 的意义在于：当我们需要自定义内存采集逻辑（比如写一个自动化测试脚本，定期采集特定进程的内存分布），可以参考 libmeminfo 的实现来编写你自己的采集工具，而不是反复调用 `dumpsys` 命令再解析文本输出。

[已验证: AOSP, system/memory/libmeminfo (Android 11+); 旧版路径 system/core/libmeminfo 已弃用]
[已验证: 官方文档, https://source.android.com/docs/core/debug/eval-performance]
[待验证: procrank 在 Android 14+ 设备上的可用性]

## Graphics / dma-buf 内存怎么查

当 `dumpsys meminfo` 里的 `Graphics` 持续上涨，或者 `showmap` 里出现大块 `/dev/dmabuf` 映射时，应该优先走图形内存排查路径。Bitmap 像素、SurfaceView / TextureView buffer、WebView 渲染缓存、视频解码输出，很多都落在 Graphic Buffer / dma-buf 上，heapprofd 看不到。

### 一条够用的排查顺序

1. **看 `dumpsys meminfo`**：把 `Graphics`、`Native Heap` 和 `TOTAL PSS` 放在一起看。`Native Heap` 涨而 `Graphics` 平稳，优先走 heapprofd / malloc debug；`Graphics` 涨得快，优先走图形内存路径；两者一起涨时，再同时看 JNI 分配和 buffer 生命周期。
2. **看 `showmap` / `smaps`**：用 `adb shell showmap <pid>` 或 `/proc/<pid>/smaps` 确认是否有大的 `/dev/dmabuf`、图形映射或匿名图像缓存。这里能回答“涨的是 native heap 还是图形映射”。
3. **对照 SurfaceFlinger**：图片、视频、WebView、SurfaceView、Camera 预览这类场景，再看 `adb shell dumpsys SurfaceFlinger`，确认对应 layer、buffer 尺寸、数量和 composition type。buffer 比显示区域大、surface 数量异常、旧 layer 没及时释放，往往比 Java 堆更接近根因。
4. **回到 Perfetto 对时间线**：把内存上涨的时间点和 `SurfaceFlinger`、`BufferQueue`、`gpu.renderstages`、解码线程 / RenderThread 活动放到同一时间窗里看，分清是 bitmap 解码峰值、视频帧缓存堆积，还是几何变化引起的 buffer 重建。

这一组工具和 §2.15 [DMA-BUF 与 Gralloc](../../part1-fundamentals/ch02-rendering/15-dmabuf-gralloc.md) 是配套的。这里解决“怎么查”，那一节解释这些 buffer 为什么会占内存、为什么会跨进程共享。

## malloc debug 与 malloc hooks：Native 内存调试的利器

### 解决的问题

前面提到的 heapprofd 适合"看趋势"——它告诉你谁在分配、分配了多少。但如果我们需要更精确的调试信息（比如"这次 `free` 对应的 `malloc` 是在哪里调的"、"有没有 double free"、"有没有 use-after-free"），就需要 malloc debug 或 malloc hooks 了。

### malloc debug

malloc debug 是 Android 系统自带的 Native 内存调试工具，从 API 24 开始提供。它通过一个 shim 层拦截进程的所有 `malloc`/`free` 调用，在每次分配和释放时记录额外的调试信息。

启用方式：

```bash
# 方式一：通过系统属性
adb shell setprop libc.debug.malloc.program com.example.myapp
adb shell setprop libc.debug.malloc.options "backtrace_enable_on_signal leak_track"
# 重启应用后生效

# 方式二：通过 wrap 属性（推荐）
# 设置 wrap 属性，应用冷启动时会加载环境变量
adb shell setprop wrap.com.example.myapp '"LIBC_DEBUG_MALLOC_OPTIONS=backtrace_enable_on_signal logwrapper"'
# force-stop 后冷启动应用
adb shell am force-stop com.example.myapp
adb shell am start -n com.example.myapp/.MainActivity
```

`backtrace_enable_on_signal` 模式下，应用启动时默认不采集分配栈，收到实时信号后才切换状态。按 bionic `malloc_debug` README，这个开关信号是 `SIGRTMAX-19`（Android 上通常是 45）：

```bash
# 切换 backtrace 采集开关
adb shell kill -45 <pid>
```

如果同时启用了 `backtrace` 选项，Android 9+ 还可以用 `SIGRTMAX-17` 把当前堆分配信息写到文件，默认路径通常是 `/data/local/tmp/backtrace_heap.<pid>.txt`：

```bash
adb shell kill -47 <pid>
adb shell ls /data/local/tmp/backtrace_heap.<pid>.txt
```

Android 14 新增 `SIGRTMAX-16`（信号值 48），用于触发 `libmemunreachable` 扫描并报告内存泄漏。这对 Native 内存泄漏的在线/离线快速诊断非常有价值：

```bash
# Android 14+: 触发 libmemunreachable 泄漏扫描
adb shell kill -48 <pid>
# 扫描结果写入 logcat，搜索 "LEAK" 关键字
adb logcat -s libmemunreachable
```

[已验证: AOSP bionic/libc/malloc_debug/README.md, Android 14 signal table]

### malloc hooks

malloc hooks 是更底层的 API，从 API 28 开始提供。它允许你注册自定义的回调函数，在每次 `malloc`/`free` 被调用时都会触发。这为构建自定义的内存分析工具提供了基础。

bionic 的 malloc hooks 通过函数指针实现。需要在进程启动时（通常在 `.init_array` 或 `android_device_setup` 中）设置这些指针：

```c
#include <malloc.h>
#include <unistd.h>

// 保存原始函数指针
static void* (*orig_malloc_hook)(size_t, const void*) = nullptr;
static void  (*orig_free_hook)(void*, const void*)   = nullptr;

// 自定义 hook 函数
static void* my_malloc_hook(size_t size, const void* caller) {
    // ⚠️ 注意：避免在 hook 中调用 malloc，会递归触发
    void* ptr = orig_malloc_hook ? orig_malloc_hook(size, caller) : malloc(size);
    return ptr;
}

static void my_free_hook(void* ptr, const void* caller) {
    if (orig_free_hook) {
        orig_free_hook(ptr, caller);
    } else {
        free(ptr);
    }
}

// 初始化：保存旧值并注册新 hook
__attribute__((constructor))
static void install_hooks() {
    orig_malloc_hook = __malloc_hook;
    orig_free_hook   = __free_hook;
    __malloc_hook    = my_malloc_hook;
    __free_hook      = my_free_hook;
}
```

关键注意事项：

- **线程安全**：bionic 的 `__malloc_hook`/`__free_hook` 不是原子操作，多线程并发设置时存在竞态条件，应在启动早期（单线程阶段）完成注册
- **递归风险**：hook 函数内部如果调用 `printf`、`std::string` 等会触发 `malloc` 的函数，会导致无限递归崩溃
- **启用方式**：API 28+ 需要通过属性 `adb shell setprop libc.debug.hooks.enable 1` 或环境变量 `LIBC_HOOKS_ENABLE=1` 启用。注意 `libc.debug.malloc.options` 属于 malloc debug 的开关，不是 hooks 的启用入口
- **API 可见性**：`__malloc_hook`/`__free_hook`/`__realloc_hook`/`__memalign_hook` 在 bionic `malloc.h` 中声明（`__INTRODUCED_IN(28)`，API 28+ 可用）。使用前需通过属性 `libc.debug.hooks.enable` 或环境变量 `LIBC_HOOKS_ENABLE` 启用，且 hook 指针设置无线程安全保证

malloc hooks 的典型应用场景包括：构建轻量级的内存分配追踪器、实现自定义的内存统计面板、集成到自动化测试中检测特定操作引入的内存分配。

malloc hooks 会拦截所有 native 分配调用，对性能有显著影响（通常 2-5 倍的分配延迟），不适合在 release 版本中启用。

[已验证: AOSP bionic/libc/malloc_hooks/]
[适用版本: malloc debug API 24+, malloc hooks API 28+]

## HWASAN 与 MTE：硬件辅助的内存安全检测

### HWASAN：硬件辅助的 AddressSanitizer

HWASAN（Hardware-assisted AddressSanitizer）是 Android 上用于检测 Native 内存安全错误的工具。它能检测的问题包括：堆缓冲区溢出、栈缓冲区溢出、use-after-free、double free 等。

与传统的 ASan（AddressSanitizer）相比，HWASAN 的内存开销更低（ASan 通常需要 3-5 倍的内存，HWASAN 只需要约 1.5 倍），这使得它可以在更大的测试范围里使用。HWASAN 主要面向 AArch64 的 userdebug/eng 或专门的 HWASAN 系统镜像，是否可用取决于设备和系统构建，不是所有 Android 10+ 商用机都能直接开启。

HWASAN 的原理是利用 ARM 的 Top Byte Ignore（TBI）特性：在 64 位地址空间中，顶部 8 位（高字节）通常不用于地址翻译。HWASAN 用这 8 位给每个分配的内存块打上标签，在每次内存访问时检查标签是否匹配。如果标签不匹配，说明这次访问越界或访问了已释放的内存。

启用 HWASAN 需要重新编译 Native 代码，在编译选项中添加 `-fsanitize=hwaddress`。

### MTE：Memory Tagging Extension

MTE（Memory Tagging Extension）是 Armv8.5-A 架构引入的硬件级内存安全特性（部分文档和营销材料将其归入 ARM v9，但技术规范上从 Armv8.5-A 起可选）。它依赖硬件、内核和系统一起支持，近几代高端 SoC 与部分 Pixel 设备开始提供这项能力。

MTE 与 HWASAN 的目标相同——检测内存安全错误——但实现方式完全不同。MTE 在硬件层面为每个内存块（通常是 16 字节粒度）分配一个标签（tag），同时在指针中嵌入相同的标签。CPU 在每次内存访问时自动检查标签是否匹配。如果不匹配，触发异常。

MTE 与 HWASAN 的适用场景不同：

- **MTE**：性能开销较低，适合低开销检测和生产环境抽样。ASYNC 不是“只记录日志不崩溃”：tag mismatch 会在最近的内核入口以 `SIGSEGV` 终止进程，只是错误地址和访问类型不如 SYNC 精确。检测粒度受 16 字节 tag 限制，对同一 tag 块内的越界访问可能漏报。
- **HWASAN**：依赖编译器插桩，需要重新编译目标代码。性能开销较高（10-20%），但诊断信息更完整，能提供精确的分配/释放调用栈，适合测试阶段的深度排查。

Android 已在部分系统组件和设备上逐步引入 MTE 支持。对于应用开发者来说，在支持 MTE 的设备上可以通过 `android:memtagMode="async"` 或开发者选项启用异步 MTE 模式；它适合测试和灰度采样，但命中 tag mismatch 后仍应按进程崩溃处理。

[已验证: 官方文档, https://developer.android.com/ndk/guides/sanitizers]
[已验证: 官方文档, https://source.android.com/docs/security/test/memory-safety]

### MTE 三种模式与 Asymmetric（ASYMM）升级机制

MTE 除了常见的 sync 和 async 两种模式，实际硬件（Arm v8.7-A+）还支持第三种——**Asymmetric（ASYMM）模式**，Android 系统对 App 透明使用：

| 模式 | 读取检查 | 写入检查 | 性能 | 生产可用性 |
|------|---------|---------|------|---------|
| SYNC | 立即 SIGSEGV | 立即 SIGSEGV | 高开销 | 仅测试 |
| ASYNC | 延迟 SIGSEGV | 延迟 SIGSEGV | **1-2%** | ✅ 可用 |
| ASYMM | 立即 SIGSEGV | 延迟 SIGSEGV | 接近 ASYNC | **✅ 推荐** |

**ASYMM 的优势**：读取越界（use-after-free read）提供精确错误位置，写入越界保持低开销。在 SPEC INT 2006 实测中，SYNC 最高可达 6.64x 减速，ASYMM 保持在 1-2% 区间（Pixel 8/9，来源：arxiv:2405.02735）。

**Android 系统行为**：App 通过 `android:memtagMode="async"` 请求 MTE 时，如果硬件支持 ASYMM，OS 自动静默升级到 ASYMM，无需 App 感知。系统组件（蓝牙 / NFC / 网络 daemon）以 ASYNC 模式运行，实际也受益于 ASYMM 硬件。

**检测 ASYMM 支持**：`cat /proc/cpuinfo` 中显示 `mte mte3` 表示 ASYMM 可用；仅有 `mte` 表示仅支持 SYNC/ASYNC（Arm v8.5-A）。

**sysfs 控制**：`/sys/devices/system/cpu/cpu<N>/mte_tcf_preferred`（root）可设置 per-CPU preferred 模式为 `async` / `sync` / `asymm`。

**默认状态边界**：第三方 App 未声明 `android:memtagMode` 时默认关闭；Compatibility Framework 中的 `NATIVE_MEMTAG_ASYNC` 和 `NATIVE_MEMTAG_SYNC` 默认也不对所有 App 强制打开。系统组件和 OEM 组件可以通过产品配置启用 MTE，不能把“App 默认关闭”推广成“整个系统默认关闭”。

**Scudo 协作**：Android 默认堆分配器 Scudo（Android 11+）通过 `IRG`（生成随机 tag）和 `STG`（存储 tag）指令与 MTE 协作。仅 Primary 分配（< 0x10000 字节）应用 MTE tag。

[已验证: Android MTE 官方文档 / MTE configuration，ASYNC 触发延迟 SIGSEGV，App 默认需显式启用]
[来源: arxiv:2405.02735 - ARM MTE Performance in Practice]
[来源: AOSP frameworks/base/core/java/com/android/internal/os/Zygote.java]


## 工具选择指南

在实际工作中，选择哪个工具取决于你要解决的问题类型。下面这张对照表可以帮助你快速定位。

**场景：Java 堆内存持续增长，怀疑泄漏**

- 第一步：用 `dumpsys meminfo` 确认 Java Heap 是否持续增长
- 第二步：用 LeakCanary 自动检测 Activity/Fragment 级别的泄漏
- 第三步：如果 LeakCanary 没有检出，用 MAT 分析 hprof 文件中的引用链

**场景：Native 堆内存异常**

- 第一步：用 `dumpsys meminfo` 确认 Native Heap 的大小和趋势
- 第二步：用 `showmap` 查看 `[anon:libc_malloc]` 区域的详细大小
- 第三步：用 heapprofd 采样 Native 分配，找到分配最多的调用栈

**场景：应用被 LMK 频繁杀掉**

- 第一步：用 `procrank` 查看全系统的内存占用排名
- 第二步：用 `dumpsys meminfo` 确认自己应用的 PSS 是否过大
- 第三步：根据 PSS 构成（Java Heap vs Native Heap vs Graphics）选择对应的优化路径

**场景：Native 内存越界访问或 use-after-free**

- 开发阶段：启用 HWASAN 或 MTE 异步模式检测内存安全错误
- 测试阶段：使用 malloc debug 的 backtrace 功能捕获具体的错误调用栈

[图：内存分析工具选择决策流程图]

## 与其他章节的关系

本章介绍的工具分别对应了不同章节中讨论的内存问题。

- 第 10.1 节（App 内存分析）中讨论的内存分析方法论，就是用本节工具来执行的
- 第 10.2 节（内存泄漏）中的 Java 泄漏检测，直接依赖 LeakCanary 和 MAT
- 第 10.3 节（内存持续增长）中的排查流程，第一步就是 `dumpsys meminfo` 趋势对比
- 第 14.1 节（Android Studio Profiler）中的 Memory Profiler，是 MAT 之外的另一种 hprof 分析方式
- 第 4.2 节（Linux 内核内存管理）和第 4.3 节（ART 虚拟机内存管理）中讨论的内存管理机制，是理解这些工具输出数据的基础

## 常见问题与误区

**误区一："有了 LeakCanary 就不需要学 MAT 了"**

LeakCanary 只能检测它预设的组件类型（Activity、Fragment、ViewModel、Service）的泄漏。如果你有一个自定义的长生命周期对象（比如单例管理器）持有了一个本该释放的大对象，LeakCanary 不会报警。这种情况只能通过 MAT 手动分析 hprof 文件来发现。

**误区二："dumpsys meminfo 的 TOTAL 就等于应用实际占用的内存"**

`dumpsys meminfo` 报告的是 PSS，其中包含了按比例分摊的共享内存。TOTAL PSS 反映的是"这个进程对系统内存压力的贡献"，不是"杀掉这个进程能释放多少内存"。后者应该看 USS（Unique Set Size）。

**误区三："heapprofd 能直接告诉我哪里泄漏了"**

heapprofd 告诉你的是"哪里在分配内存"和"哪些分配没有被释放"。它不会自动判断泄漏——因为"分配了但没释放"不一定等于泄漏，可能只是对象生命周期还没结束。你需要结合业务逻辑来判断 heapprofd 发现的"未释放分配"是否真的是泄漏。

**误区四："MAT 分析 hprof 文件可以在线上用"**

`Debug.dumpHprofData()` 会导致应用暂停（stop-the-world），暂停时间与 Java 堆大小成正比，通常几百毫秒到数秒。在线上环境抓取 hprof 会严重影响用户体验。线上场景应该使用 Android Studio Profiler 的实时监控或 heapprofd 的采样模式。

**误区五："Native 内存问题只发生在使用 JNI 的应用中"**

即使你的应用没有直接写 JNI 代码，Android 图形栈也会占用大量非 Java 内存。Bitmap 像素、Surface buffer、WebView 渲染缓存可能出现在 `Native Heap`、`Graphics` 或 `/dev/dmabuf`。看到内存上涨后，先分清是 `malloc` native heap 还是 Graphic Buffer / dma-buf，再决定用 heapprofd 还是图形内存那组工具。

## 参考资料

- LeakCanary 官方文档：https://square.github.io/leakcanary/
- MAT 下载与文档：https://eclipse.org/mat/
- 高爷 MAT 三部曲（入门）：https://www.androidperformance.com/2015/04/11/AndroidMemory-Usage-Of-MAT/
- 高爷 MAT 三部曲（进阶）：https://www.androidperformance.com/2015/04/11/AndroidMemory-Usage-Of-MAT-Pro/
- 高爷 MAT 三部曲（Bitmap）：https://www.androidperformance.com/2015/04/11/AndroidMemory-Open-Bitmap-Object-In-MAT/
- heapprofd 官方文档：https://perfetto.dev/docs/data-sources/native-heap-profiler
- dumpsys meminfo 官方文档：https://developer.android.com/studio/command-line/dumpsys#meminfo
- Android 内存调试工具总览：https://developer.android.com/ndk/guides/sanitizers
- AOSP libmeminfo 源码：https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-16.0.0_r1/
- Android 调查内存使用：https://developer.android.com/topic/performance/memory
