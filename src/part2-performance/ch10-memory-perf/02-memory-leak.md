---
title: "内存泄漏"
chapter: "10.2"
section: "10.2"
status: ready-for-review
drafted_date: "2026-04-02"
drafted_by: "openclaw-task2a"
applicable_versions: "Android 8.0 (API 26) - Android 17 (API 37)"
last_verified: "2026-04-02"
last_verified_against: "AOSP android-16.0.0_r1"
confidence: high
reviewed_date: "2026-05-07"
reviewed_by: openclaw-task6
polish_count: 1
polish_date: "2026-04-08"
polish_by: "task2b-polish"
sources:
  - type: blog
    path: "Personal-Knowlodge/source/2026-03-07_wechat_为什么各大厂自研的内存泄漏检测框架都要参考_LeakCanary_因为它是真强啊.md"
  - type: blog
    path: "性能优化日报/2026-03-15-LeakCanary-内存泄漏检测.md"
  - type: paper
    path: "Manus/android_native_memory_leak_report.md"
  - type: official
    path: "source.android.com/docs/debug/native-memory"
  - type: official
    path: "perfetto.dev/docs/data-sources/native-heap-profiler"
tags: ['memory-leak', 'leakcanary', 'mat', 'heapprofd', 'heap-dump', 'gc-root', 'native-memory']
related_chapters: ["4.1", "4.3", "4.5", "10.1", "10.6"]
pipeline_stage: "task2b_pending"
task2b_result: fixed
task2b_state: "pending"
task6_state: reviewed
task6_result: pass-light-edit
task9_state: "reviewed"
task9_reviewed_date: "2026-05-08"
task9_reviewed_by: "openclaw-task9"
last_task9_at: "2026-05-08T00:28:41+08:00"
task9_review_notes: "2026-05-03 04 task9 deep-review: needs-rework。P0 0 / P1 2 / P2 0。 | 2026-05-08 00:28 Task9 deep-review: needs-rework。P0 1 / P1 1 / P2 1。Top: ASan/HWASan 被误写成泄漏检测工具且 ASan 版本边界错到 API 26。"
task9_result: "needs-rework"
last_task6_at: "2026-05-07T23:13:13+08:00"
task6_review_notes: "2026-05-07 23:13 task6 revisiting-review: pass-light-edit。修复禁用词、无语言代码块、比喻化开头与少量措辞问题；Task9 历史技术项仍待复审，未自动晋升。"
---

# 内存泄漏

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 内存泄漏的定义：对象不再使用但无法被 GC 回收
- 🔹 LeakCanary 的原理：WeakReference + ReferenceQueue + Heap Dump
- 🔹 常见泄漏模式：Activity 泄漏、Fragment 泄漏、Handler 泄漏、Listener 未解注册
- 🔹 Native 内存泄漏的排查方法：malloc debug / heapprofd
- 🔹 Heap Dump 分析：GC Root → Reference Chain → Leaked Object

### 扩展（可选深入）

- 🔸 Compose 场景的内存泄漏特征
- 🔸 线上内存泄漏的自动检测方案

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解内存泄漏

做过 Android 性能优化的工程师，大概率都遇到过这样的场景：应用用着用着就越来越卡，最终 OOM 崩溃；打开 Android Studio 的 Memory Profiler，看到内存曲线像台阶一样只升不降。尝试分析 OOM 时的堆栈日志，却发现堆栈指向的可能只是一次普通的字符串分配——持续占用内存的那些泄漏对象，早已在之前无数次页面跳转和配置变更中积累。

内存泄漏通常不会立刻把应用打崩，而是让可用内存在长时间运行中持续减少。等到问题暴露时，面前是一批积累了几十分钟的泄漏对象，要从中找出最早失效的引用链很难。

了解内存泄漏的核心目的只有一个：**在泄漏发生的瞬间就捕获它，而不是等到 OOM 时再回头找。**

## 内存泄漏的定义

[已验证: 官方文档, developer.android.com/topic/performance/memory]

所谓内存泄漏，就是：**一个对象已经不再被程序使用了，但由于存在一条从 GC Root 到该对象的引用链，垃圾回收器无法判定它为垃圾，因此不会回收它。**

在 ART 虚拟机中，垃圾回收器判定对象是否存活的方法是"可达性分析"（Reachability Analysis）。从一组被称为 GC Root 的特殊对象出发，沿着引用链向下追踪。如果一个对象到任何一个 GC Root 之间没有任何引用链相连，那这个对象就是不可达的，可以被回收。

### 什么是 GC Root

在 Android/ART 中，以下几类对象是 GC Root：

- **栈帧中的局部变量**：当前正在执行的方法中的局部引用。只要方法还没返回，它们引用的对象就不会被回收。
- **静态字段**：类的 static 字段，生命周期等于类的生命周期，而类一旦加载就几乎不会被卸载。
- **JNI Global Reference**：Native 代码通过 `NewGlobalRef()` 创建的全局引用。如果不显式调用 `DeleteGlobalRef()`，这些引用会一直存在。
- **活跃的线程对象**：正在运行的 Thread 对象本身就是 GC Root。

理解了 GC Root，内存泄漏的定义就非常清晰了：**泄漏就是一条不应该存在的、从 GC Root 到"已死亡"对象的引用链。**

[图：GC Root → 引用链 → 泄漏对象 的示意图]

内存泄漏有两种不同的语境。开发者常说的"内存泄漏"一般是指 Java 堆上的泄漏。而在 Native 层，内存泄漏指的是通过 `malloc`/`new` 分配的内存没有被 `free`/`delete` 释放——这和 GC 无关，纯粹是开发者的手动管理失误。两种泄漏的症状相似（内存持续增长），但排查方法完全不同。

理解泄漏的成因后，接下来要解决的是发现时机。在 Java 堆上，开发阶段最常用的工具是 LeakCanary。这个库在开发阶段的内存泄漏检测方面已经接近行业标准，后续不少线上检测方案也沿用了类似思路。

## LeakCanary：开发阶段的自动检测

[已验证: LeakCanary 2.x 源码, square.github.io/leakcanary]
[已验证: 来源见 Personal-Knowlodge/source/2026-03-07_wechat_为什么各大厂自研的内存泄漏检测框架都要参考_LeakCanary_因为它是真强啊.md]
[已验证: 来源见 性能优化日报/2026-03-15-LeakCanary-内存泄漏检测.md]

### 工作原理：WeakReference + ReferenceQueue

LeakCanary 的检测机制巧妙地利用了 Java 引用体系中的一个特性：当一个对象只被 WeakReference 引用时，下次 GC 会回收它，同时 JVM 会把这个 WeakReference 对象放入它关联的 ReferenceQueue 中。

Android 17（API 37）引入分代 CMC（Concurrent Mark-Compact），理论上对年轻代 WeakReference 入队延迟有改善空间——分代 GC 允许在 Minor GC 阶段处理年轻代中的弱引用对象，减少等待 Major GC 的概率。但当前缺乏 ART reference processing 的源码提交或官方 benchmark 支撑具体延迟数据；CC collector 在 Android 10+ 已默认 generational，Android 17 分代 CMC 对 ReferenceQueue/WeakReference 处理时机的增量效果尚待验证。（[待验证：Android 17 分代 CMC 是否显著缩短 LeakCanary watchDuration 前后的响应时间]）

工作流程：

**第一步：感知对象销毁时机。** 通过注册 ActivityLifecycleCallbacks、FragmentLifecycleCallbacks 等回调，在 Activity 执行完 `onDestroy()` 时就知道这些对象"应该"不再被使用了。

**第二步：包装 WeakReference 并等待 GC。** 为每个"应该死亡"的对象创建 KeyedWeakReference，关联到 ReferenceQueue。等待 5 秒，期间主动触发 `Runtime.getRuntime().gc()`。

**第三步：判断是否泄漏。** 如果 GC 之后 WeakReference 没有出现在 ReferenceQueue 中，说明对象没有被回收——发生了泄漏。

**第四步：Heap Dump + 分析。** 泄漏对象数量达到阈值时，调用 `Debug.dumpHprofData()` 生成 Heap Dump，用 Shark 引擎找出从 GC Root 到泄漏对象的最短引用链。

```kotlin
// LeakCanary 核心检测逻辑（简化示意）
val weakRef = KeyedWeakReference(activity, referenceQueue, description)
SystemClock.sleep(WAIT_DURATION)
Runtime.getRuntime().gc()
// ReferenceQueue 没有 contains() 方法，需要 poll 取出已入队引用再判断
val queued = generateSequence { referenceQueue.poll() }.any { it === weakRef }
if (!queued) { /* 泄漏确认，触发 Heap Dump */ }
```

### 分析报告的阅读方法

LeakCanary 输出的分析报告中，最关键的信息是**引用链**（Reference Chain）：

```text
┬───
│ GC Root: Local variable in native code
├─ dalvik.system.PathClassLoader instance
│    ↓ PathClassLoader.runtimeInternalObjects
├─ java.lang.Object[] array
│    ↓ Object[].[43]
├─ com.example.Utils class
│    ↓ static Utils.helper        ← ~~~ 标记的怀疑对象
╰→ java.example.Helper instance   ← 泄漏对象
```

LeakCanary 用 `~~~` 标记"怀疑对象"——即最可能导致泄漏的那个引用。它排除了 Application 这种生命周期等于进程的对象，只标记"本该释放但没有释放"的引用。

报告还会将泄漏分为 **Application Leaks**（应用代码导致）和 **Library Leaks**（Android Framework 已知泄漏）。

## 常见泄漏模式

### Activity 泄漏：静态字段持有 Context

最常见的触发方式是让一个静态字段（或单例对象）直接持有 Activity 引用：

```kotlin
// ❌ 泄漏：静态字段直接持有 Activity
object ImageLoader {
    var context: Context? = null  // 如果传入 Activity，就会泄漏！
    fun init(context: Context) { this.context = context }
}
```

`ImageLoader` 作为 Kotlin `object`（静态单例），生命周期等于进程。正确做法是使用 Application Context 或 WeakReference。

### Handler 泄漏：内部类隐式持有外部引用

非静态内部类（包括匿名内部类）会隐式持有外部类的引用。当 Handler post 一个延迟消息时，消息持有 Handler，Handler 又持有 Activity：

```java
// ❌ 泄漏：匿名 Runnable 隐式持有 Activity
public class MainActivity extends Activity {
    private final Handler handler = new Handler();
    private void delayWork() {
        handler.postDelayed(new Runnable() {
            @Override
            public void run() { updateUI(); }
        }, 5000);
    }
}
```

解决方案：在 `onDestroy()` 中移除所有回调，或使用静态内部类 + WeakReference。

### Listener / Callback 未解注册

注册了回调但没有在合适的时机解注册。回调对象会一直被系统服务或库的内部数据结构持有。建议在 `onStop()` 而非 `onDestroy()` 中解注册——原因是多页面场景下，`onDestroy()` 的调用时机不确定，而 `onStop()` 在 Activity 不可见时必定触发，能更及时地释放引用。

### Fragment 泄漏：FragmentTransaction 和 View 的纠葛

Fragment 有两个可能泄漏的对象：Fragment 本身和它的 View。`onDestroyView()` 销毁 View 但保留 Fragment，`onDestroy()` 才销毁 Fragment。如果在 View 销毁后仍然引用它（比如在 ViewModel 或静态变量中缓存了 `fragment.view`），就会导致 View 层的泄漏——Fragment 还在，但 View 已经应该被回收了。

在 ViewPager + Fragment 的场景中，这种泄漏尤为常见：Fragment 被 FragmentPagerAdapter 缓存（`BEHAVIOR_RESUME_ONLY_CURRENT_FRAGMENT`），其 View 在页面切换时经历 destroy → recreate 循环，任何跨这个周期的引用都可能成为泄漏源。

上面讨论的都是 Java 堆上的泄漏——GC Root 引用链没断干净。但在 Android 中，还有另一类泄漏完全不受 GC 管控：Native 层通过 `malloc`/`new` 分配的内存，如果忘记 `free`/`delete`，同样会造成内存持续增长。两种泄漏的外在表现相似，排查思路却完全不同。

## Native 内存泄漏的排查

[已验证: 官方文档, source.android.com/docs/debug/native-memory]
[已验证: Perfetto 文档, perfetto.dev/docs/data-sources/native-heap-profiler]
[已验证: 来源见 Manus/android_native_memory_leak_report.md]

Native 内存泄漏指的是通过 `malloc`/`new` 分配的内存没有被 `free`/`delete` 释放。排查思路和 Java 完全不同：没有 GC Root 的概念，核心手段是**跟踪 malloc 和 free 的配对关系**。

### heapprofd：采样式的 Native 堆分析

Android 10 引入的低开销 Native 堆分析器，集成在 Perfetto 中。通过采样方式拦截 `malloc`/`free` 调用，记录分配的调用栈。

```bash
tools/heap_profile -n com.example.myapp
```

在 Perfetto UI 中，数据以火焰图和表格展示。默认采样间隔 4096 字节（可通过 `-s` 参数调整），小于 4KB 的单次分配可能被跳过，但对于持续增长的大型泄漏，这个精度足够定位问题。如果"Total allocated"持续增长而"Total freed"几乎不变，就是 Native 泄漏的信号。

### Malloc Debug：全量的 Native 内存调试

需要更精确信息时使用。通过在 malloc/free 函数前插入 shim 层拦截所有分配操作：

```bash
adb shell setprop libc.debug.malloc.options backtrace
adb shell setprop libc.debug.malloc.program com.example.myapp
```

会显著影响性能，只在调试阶段使用。Native 库需要保留符号信息。

### libmemunreachable：零开销的泄漏检测

轻量级 Native 内存泄漏检测器。对 Native 堆执行一次不精确的 mark-and-sweep，未被标记的块报告为可能的泄漏。零开销但精度较低，作为第一步筛查工具。

### ASan / HWASan：编译期内存错误检测

AddressSanitizer 和 Hardware ASan 不仅能检测泄漏，还能检测越界读写、Use-After-Free 等内存安全问题。通过编译器插桩实现，需要重新编译且增加内存占用和运行开销。

[适用版本]：ASan 支持 Android 8.0+，HWASan 需要 Android 10+ 且硬件支持

Native 泄漏排查依赖系统工具（heapprofd、Malloc Debug），而 Java 泄漏的主要分析手段是 Heap Dump——拿到进程某一时刻的完整堆快照，然后逐层追踪引用链。LeakCanary 在检测到泄漏后会自动触发 Heap Dump，但当需要在生产环境或手动排查时，我们需要独立完成这个过程。

## Heap Dump 深度分析

### 获取 Heap Dump

```bash
# 通过 adb
adb shell am dumpheap com.example.myapp /data/local/tmp/dump.hprof
# 代码中触发
Debug.dumpHprofData("/data/local/tmp/dump.hprof")
```

### MAT 分析步骤

1. **打开 .hprof 文件**，MAT 自动生成概览
2. **使用 Dominator Tree** 按 Retained Size 排序
3. **右键可疑对象 → Path To GC Roots → exclude weak/soft references**
4. **分析引用链**，找到"不应该存在"的引用

### Shark：LeakCanary 的分析引擎

Shark 可以独立使用，优势在于内存占用低、解析速度快。对于几百 MB 的 Heap Dump，Shark 可以在几秒内完成分析。

[已验证: LeakCanary/Shark 官方文档, square.github.io/leakcanary]

## 在 Perfetto / 工具中的表现

### Java 内存泄漏的 Trace 信号

在 Android Studio Memory Profiler 中，泄漏的典型表现是内存曲线呈阶梯状上升——每次打开一个 Activity 后，内存跳上一个台阶，返回后不回落。如果连续进出同一个页面 5 次，Java Heap 增长了 5 个"台阶"且长时间不降，几乎可以确定该页面存在泄漏。

在命令行中，`dumpsys meminfo <package_name>` 是最快的确认手段。重点关注两个数字：**Views** 和 **Activities**。如果 Activities 数量大于当前屏幕上实际可见的 Activity 数（通常应为 1），说明有 Activity 实例未被释放。同理，Views 数量持续增长也暗示 View 层存在泄漏。

LeakCanary 检测到泄漏后，会在系统通知栏弹出提示，同时在 Logcat 中以 `LeakCanary` tag 输出完整的引用链分析日志。开发阶段建议保持 LeakCanary 开启，每个 leak 都不应被忽略。

### Native 内存泄漏的 Trace 信号

Native 泄漏在 Perfetto 中通过 heapprofd 采集的数据来观察。在 Perfetto UI 中打开 Native Heap Track，重点看两个指标：**Total allocated**（累计分配）和 **Total freed**（累计释放）。如果 Total allocated 持续增长而 Total freed 几乎不变，两者的差值（即"当前在用"）不断扩大，就是 Native 泄漏的信号。

火焰图视图能直观展示哪些调用栈贡献了最多的未释放分配。点击火焰图中最大的色块，会展开具体调用栈和对应的源码位置。

[图：Perfetto heapprofd 火焰图示例——Total allocated vs Total freed 的差距持续扩大]

## 与其他机制的关系

- **§4.1 Android 内存模型全景**：泄漏发生在 Java 堆或 Native 堆，理解内存分区是定位前提
- **§4.3 ART 虚拟机内存管理**：GC 的可达性分析是理解 Java 内存泄漏的理论基础
- **§4.5 App 内存优化**：避免泄漏是内存优化的第一步
- **§10.1 App 内存分析**：Heap Dump 分析是 10.1 核心方法论之一
- **§10.6 内存抖动与频繁 GC**：泄漏导致可用内存减少，间接加剧 GC 频率

## 版本演进

- **Android 8.0**：ASan 支持在非 root 设备上通过 wrap.sh 使用
- **Android 10**：引入 heapprofd，集成在 Perfetto 中
- **LeakCanary 2.0 (2020)**：从 HAHA 迁移到 Shark，零代码初始化。多进程应用、direct boot、instant app 或严格沙箱模式下自动初始化可能受影响——这些边界场景下 ContentProvider 的初始化时机和 Security Context 与普通单进程应用不同。遇到自动初始化问题时，在 `Application.onCreate()` 中显式调用 `AppWatcher.manualInstall(application)` 即可
- **Android 17 (API 37)**：分代 CMC 引入独立的 Minor GC，年轻代 WeakReference 入队延迟理论上可缩短，但具体增量效果待验证（[待验证：缺乏官方 benchmark 和 ART reference processing 源码提交；CC collector 在 Android 10+ 已默认 generational，分代 CMC 的增量收益需同设备 A/B trace 对照]）
- **heapprofd Java 堆采样**：Perfetto heapprofd 支持通过 `heaps: "com.android.art"` 配置 Java heap allocations 采样，具体成为默认可用能力的 Android 版本边界待核

## 常见问题与误区

**"调 System.gc() 能解决内存泄漏"** — 不能。泄漏的原因是有引用链阻止回收，GC 运行也无法回收。手动触发 GC 反而增加卡顿。

**"Android 8.0+ 不需要 recycle Bitmap"** — Bitmap 像素数据移到了 Native 堆，但放在静态变量中的 Bitmap 仍会导致 Native 内存泄漏。

**"内存泄漏只会发生在 Activity 和 Fragment 中"** — 任何 Java 对象都可能泄漏。协程中捕获 Activity 引用但生命周期比 Activity 长就是一个常见例子。

**"LeakCanary 报告的泄漏都需要修复"** — 分为 Application Leaks 和 Library Leaks，Library Leaks 是 Framework 已知问题，开发者通常无法修复。

## [自动发现] Compose 场景的内存泄漏特征

Jetpack Compose 引入了新的泄漏场景：

- **LaunchedEffect 持有 Activity/Fragment 引用**：协程生命周期绑定到 Composition
- **rememberCoroutineScope 闭包捕获泄漏**：`rememberCoroutineScope()` 创建的协程作用域绑定到 Composition，离开 Composition 时自动取消。风险不在于 `rememberCoroutineScope` 本身，而在于把 Activity/View 引用放进超出 Composition 生命周期的外部作用域（单例、全局 callback、未清理的 Listener）——这些外部持有者不会随 Composition 销毁而释放引用
- **remember 缓存了不该缓存的对象**：持有 Context 或 View 引用
- **CompositionLocal 滥用**：跨 Activity 边界的 CompositionLocal

排查时除 LeakCanary 外，可借助 Layout Inspector 查看 Composition 树是否正确 dispose。

## [自动发现] 线上内存泄漏的自动检测方案

线上方案常见思路：

1. **监控指标**：通过 `Runtime.getRuntime()` 监控堆使用量
2. **选择性 Heap Dump**：fork 子进程执行（快手 Koom 的主要优化）
3. **服务端分析**：Shark 或自研引擎批量分析
4. **SDK 集成**：腾讯 Matrix、快手 Koom、字节 MemoryLeakDetector

Android 15+ 引入的 `ProfilingManager`（`android.os.ProfilingManager`）提供了系统级零侵入触发能力：应用可通过 `requestProfiling()` 请求系统按条件自动采集 Heap Dump 或 Perfetto Trace，无需自建监控框架即可获取内存现场。结合 `ProfilingResultCallback` 可在采集完成后获取结果路径。对于不需要自建 APM 的小中型项目，这是替代自研内存监控的官方路径。

## 参考资料

- [LeakCanary 官方文档](https://square.github.io/leakcanary/)
- [Shark 引擎源码](https://github.com/square/leakcanary/tree/main/shark)
- [Android Malloc Debug](https://source.android.com/docs/debug/native-memory)
- [heapprofd / Perfetto Native Heap Profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [快手 Koom](https://github.com/KwaiAppTeam/Koom)
- [腾讯 Matrix](https://github.com/Tencent/matrix)
- [引用: Personal-Knowlodge/source/2026-03-07_wechat_为什么各大厂自研的内存泄漏检测框架都要参考_LeakCanary_因为它是真强啊.md]
- [引用: 性能优化日报/2026-03-15-LeakCanary-内存泄漏检测.md]
- [引用: Manus/android_native_memory_leak_report.md]
