---
title: "大内存与多进程策略"
chapter: "23.6"
section: "23.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-17"
last_source_verified_at: "2026-08-17"
last_verified_against: "Android 17 / API 37 官方 App memory limits、Manage memory、ComponentCallbacks2、Binder、WebView 与 Google Play 64 位文档；AOSP android-17.0.0_r1 ActivityThread、ActivityManager、ComponentCallbacks2、TransactionTooLargeException、MemoryLimiter、ActivityManagerShellCommand、ActivityManagerService、ART thread.cc"
last_review_finalize_at: "2026-08-15T08:05:42+08:00"
last_review_finalize_run_id: "20260815-080542-gracker-writing-review"
confidence: high
sources:
  - type: official
    path: "https://developer.android.com/guide/topics/manifest/application-element#largeHeap"
  - type: official
    path: "https://developer.android.com/reference/android/app/ActivityManager#getMemoryClass()"
  - type: official
    path: "https://developer.android.com/guide/components/processes-and-threads"
  - type: official
    path: "https://developer.android.com/topic/performance/memory-management"
  - type: official
    path: "https://developer.android.com/topic/performance/memory"
  - type: official
    path: "https://developer.android.com/reference/android/content/ComponentCallbacks2"
  - type: official
    path: "https://developer.android.com/google/play/requirements/64-bit"
  - type: official
    path: "https://developer.android.com/reference/android/os/TransactionTooLargeException"
  - type: official
    path: "https://developer.android.com/reference/android/webkit/WebView#getWebViewRenderProcess()"
  - type: official
    path: "https://developer.android.com/guide/components/activities/process-lifecycle"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/thread.cc"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerService.java"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp"
  - type: aosp
    path: "https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/TransactionTooLargeException.java"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 虚拟内存优化（上）：线程+多进程优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 物理内存优化实战：Java Heap 内存优化.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：掌握 App 运行时的内存模型.md]"
  - type: blog
    path: "[结构参考: Clippings/Android 性能优化 - 原理：重新认识内存.md]"
tags: [large-heap, multiprocess, memory-budget, 64bit]
related_chapters: ["23.4", "4.4", "1.3", "4.7"]
pipeline_stage: finalized
last_draft_polish_at: "2026-08-15T08:05:42+08:00"
last_draft_polish_run_id: "20260815-080542-gracker-writing"
last_idle_audit_at: "2026-08-17T18:40:06+08:00"
last_idle_audit_run_id: "20260817-183500-idle-audit-6907b226"
task9_state: reviewed
task2b_state: fixed
task6_state: reviewed
consolidated_from:
  - "src/part5-app/ch23-memory-practice/09-android17-app-memory-limits.md"
---

# 大内存与多进程策略

> **版本基线**
>
> 平台源码统一以 Android 17 / API 37 / `android-17.0.0_r1` 为锚点；涉及 `/proc` 与虚拟地址空间时，内核侧以 `android17-6.18-2026-06_r6` 为基线。历史版本只用于说明兼容边界，最高版本为 Android 17。

## 为什么要了解大内存与多进程策略

大内存问题常涉及两类限制：Java 堆增长上限，以及进程可用的虚拟地址范围。Java 堆存放由 ART 管理的 Java / Kotlin 对象；虚拟地址范围决定 32 位进程能否继续用 `mmap`（内存映射系统调用）为线程栈、`.so`、`.dex`、Bitmap、图形缓冲或匿名内存保留地址区间。

`android:largeHeap`、多进程和 64 位迁移改变的边界各不相同。`largeHeap` 提高应用进程的 ART 堆增长上限；多进程让组件使用独立的地址空间和运行时，也会重复支付进程级内存成本；64 位迁移扩大可用虚拟地址范围，同时可能增加指针及部分原生数据结构的大小。这三种手段都不会自动降低按比例分摊集（PSS，共享页按参与进程数分摊后的物理内存统计），也不会消除泄漏。

选择方案前应按失败类型定位。Java 堆 OOM（内存不足异常）可参阅 [23.4 Java 堆优化策略](./04-java-heap-optimization.md)；低内存终止进程可参阅 [4.4 系统内存压力与 lmkd](../../part1-fundamentals/ch04-memory/04-lmk.md)，其中 lmkd 是 Android 根据系统内存压力终止低优先级进程的守护进程。`pthread_create`、`mmap` 或动态链接器报错时，还要检查线程数、映射布局、应用二进制接口（ABI，规定指令集、调用约定和二进制布局）及资源限制。WebView、图形内存或原生内存增长，则要继续定位实际分配者。

Android 17 在部分设备上启用了按设备总 RAM 制定的应用内存限制，用于约束极端泄漏和异常占用。它适用于所有运行在 Android 17 上的应用，不受 `targetSdkVersion` 影响；设备是否启用、当前限制是多少，都要现场查询。`largeHeap` 和拆分进程不会绕过这套限制，退出识别与诊断方法见“Android 17 应用内存限制”。

## `largeHeap` 的使用场景与代价

`android:largeHeap="true"` 写在 `<application>` 元素上。官方文档给出了三个边界：设置作用于该应用创建的所有进程；同一进程采用第一个载入应用的设置；采用共享 UID 并共用进程的多个应用必须保持设置一致。设备提供的大堆内存等级（`large memory class`，大堆模式下建议的 Java 堆容量，单位 MB）可能与普通内存等级相同，因此开启属性不保证增加固定容量。

Android 17 的 `ActivityThread.handleBindApplication()` 检查 `ApplicationInfo.FLAG_LARGE_HEAP`：设置了该标志时调用 `VMRuntime.getRuntime().clearGrowthLimit()`，否则调用 `clampGrowthLimit()`。`ActivityManager.getMemoryClass()` 读取 `dalvik.vm.heapgrowthlimit`，`getLargeMemoryClass()` 读取 `dalvik.vm.heapsize`。这些代码只改变 ART Java 堆限制，不会减少原生堆、图形内存、线程栈或文件映射。

源码可查阅 AOSP `android-17.0.0_r1` 的 [`ActivityThread.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java) 与 [`ActivityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java)。

适合打开 `largeHeap` 的场景很少，通常要同时满足三个条件：

- 峰值来自短时存在的 Java 对象或大数组，而且对象生命周期、缓存、Bitmap 和流式处理已经优化；主要增长来自原生内存、图形内存或线程栈时，`largeHeap` 无法处理对应分配。
- 高内存操作具有明确的起止范围，例如大图编辑、离线地图切片、批量导入或复杂文档解析；长期驻留的缓存不应依靠 `largeHeap` 扩容。
- 应用能按设备状态降低资源规格：在低内存设备、32 位进程、后台或设备过热时，降低分辨率、单批数据量、并发数或缓存上限。

这段函数读取普通和大堆内存等级、当前进程的 `Runtime.maxMemory()`，以及低内存设备标志。它们只能用于制定策略，不能表示此刻仍可成功分配的字节数。

```kotlin
data class HeapPolicyInputs(
    val normalClassMb: Int,
    val largeClassMb: Int,
    val runtimeMaxBytes: Long,
    val largeHeapEnabled: Boolean,
    val lowRamDevice: Boolean
)

fun readHeapPolicyInputs(context: Context): HeapPolicyInputs {
    val am = context.getSystemService(ActivityManager::class.java)
    val largeHeapEnabled =
        (context.applicationInfo.flags and ApplicationInfo.FLAG_LARGE_HEAP) != 0

    return HeapPolicyInputs(
        normalClassMb = am.memoryClass,
        largeClassMb = am.largeMemoryClass,
        runtimeMaxBytes = Runtime.getRuntime().maxMemory(),
        largeHeapEnabled = largeHeapEnabled,
        lowRamDevice = am.isLowRamDevice
    )
}
```

缓存预算还要结合对象实测大小、并发峰值、重建成本、前后台状态和其他内存类型，不能直接用内存等级乘一个通用比例。`Runtime.maxMemory()` 只描述当前 ART Java 堆上限；原生内存与图形内存仍需单独测量。

`largeHeap` 的代价主要有四类：

- GC 成本可能增加：`largeHeap` 本身不会创建对象；应用若用新增空间保留更多对象，垃圾收集器需要处理的存活对象集合随之增大，标记、复制或压缩的工作量也会增加。相关机制见 [23.4 Java 堆优化策略](./04-java-heap-optimization.md) 和 [4.7 ART 分代 GC、Region 碎片与暂停分析](../../part1-fundamentals/ch04-memory/07-art-generational-gc.md)。
- 系统回收压力增加：PSS 上升后，lmkd 在系统内存紧张时更容易终止缓存进程或其他低优先级进程。进程优先级与终止条件见 [4.4 系统内存压力与 lmkd](../../part1-fundamentals/ch04-memory/04-lmk.md)。
- 问题被延后暴露：泄漏、无界缓存和错误的批处理大小可能从“快速 OOM”变成“运行更久后卡顿或被杀”。
- 多进程统计更复杂：该属性作用于应用创建的所有进程；共享 UID 或同一进程载入多个应用时，还要满足前述一致性要求，不能只查看单个组件。

评估 `largeHeap` 时，应在同一设备、场景和输入下比较 Java 堆存活量、分配速率、GC、PSS、驻留集大小（RSS，进程当前映射到物理内存的全部页面），以及 Android 17 记录的退出原因。OOM 未再出现，只说明当前测试没有在原有 Java 堆上限处失败，系统内存压力仍可能上升。

## 多进程内存隔离与共享

Android 默认让同一应用的组件运行在一个 Linux 进程和主线程中。进程是拥有独立虚拟地址空间的执行容器；组件可用清单中的 `android:process` 指定其他进程。跨进程通信（IPC）常通过 Binder 完成：Binder 把参数序列化到 `Parcel`，再把事务送到目标进程。远程调用进入服务进程后，由系统维护的 Binder 线程池执行，因此服务端方法要能安全处理多个并发调用。进程模型及生命周期见 [1.3 进程模型与生命周期管理](../../part1-fundamentals/ch01-architecture/03-process-model.md)。

多进程可以隔离地址空间、组件生命周期和崩溃影响范围。例如，将图片编辑、插件运行时或边界清楚的批处理服务放入独立进程后，系统回收该进程会同时释放其 Java 堆、原生堆、线程栈、即时编译（JIT）缓存和文件映射。应用不应把主动终止子进程当作常规资源释放接口：Android 会根据活跃组件、进程重要性和系统资源决定进程寿命。任务完成时应停止 `Service`、解除绑定并保存结果，让组件状态如实表示是否仍有工作。

拆成多个进程不会自动减少应用总内存。每个进程都有独立的 ART 运行时、类加载器（`ClassLoader`）、线程、Binder 线程池、原生内存分配器状态和业务缓存。`.so`、`.dex` 与 Android 框架的只读代码页可以共享；被进程修改后的脏页、Java 对象、线程栈和多数原生分配不能共享。PSS 将共享页按参与进程数分摊，私有页全额计入当前进程；RSS 计算较快，却会在每个进程中完整计算共享页，因此不能把多个进程的 RSS 直接相加当作应用物理内存总量。

适合拆进程的模块通常有这些特征：

- 峰值高且生命周期清楚：任务完成后没有继续活跃的组件或绑定关系，系统可以将该进程转为缓存进程（`cached process`，即当前没有用户可感知工作、可按需回收的进程）。
- 需要隔离崩溃：原生代码崩溃、WebView 渲染进程异常或插件崩溃不应同时终止主进程。
- 跨进程输入输出可以表示为文件路径、统一资源标识符（URI）、文件描述符等资源句柄、任务 ID 或小型结果对象。句柄只引用资源，不携带资源的全部内容。
- 启动开销可测量：子进程冷启动、`ClassLoader` 初始化，以及该进程中的 `ContentProvider` 初始化都已纳入目标操作的耗时测量。

不适合拆进程的模块也要明确：高频小调用、强共享内存状态、需要大量 Java 对象跨进程传输、每次都要同步 UI 状态的模块，拆出去后很容易把内存问题换成 Binder 成本、序列化成本和一致性问题。

一种常见拆分方式是：主进程只保留任务调度和少量状态，独立进程处理边界明确的任务。服务按任务 ID 读取输入，将产物写入文件或数据库，Binder 只返回状态和结果引用。Binder 事务缓冲区当前为每个进程固定 1 MB，并由该进程所有正在执行的事务共享；即使单次参数不大，并发事务也可能触发 `TransactionTooLargeException`。大数组和 Bitmap 因此不应直接写入 `Parcel`。

大数据可以通过 `ContentProvider`、`ParcelFileDescriptor`、文件或 `SharedMemory` 共享内存接口传递句柄，同时规定关闭时机、访问权限和并发读写协议。句柄会减少 `Parcel` 内的数据量，但数据本身仍有内存和 I/O 成本。

WebView 需要单独统计。从 Android 8.0（API 26）起，WebView 可在多进程模式下使用与应用进程隔离的沙箱渲染进程。同一应用进程中的多个 WebView 可能共享渲染进程，该渲染进程不会与其他应用进程共享。把承载 WebView 的 `Activity` 放入应用自定义进程，只会再增加一个应用进程，不会合并或替代 WebView 渲染进程。`WebView.getWebViewRenderProcess()` 从 API 29 起可返回关联渲染进程的句柄；测量时应区分主进程、WebView 宿主进程、渲染进程和 GPU 使用量。

## 进程内存预算管理

预算应按“进程 × 内存类型 × 场景”分别记录，不能只为整个应用设一个总数。主进程要控制常驻 PSS 和缓存，WebView 宿主进程要连同沙箱渲染进程测量，图片编辑进程要区分 Bitmap、原生内存和图形内存，播放器进程还要统计解码缓冲与图形表面（`surface`）。

开发测试时可先用 `dumpsys meminfo` 建立基线，再采集 Java 堆转储、原生堆分配、Perfetto 内存计数器或生产环境抽样。`dumpsys meminfo` 能显示 PSS、private dirty（只由当前进程修改且无法与其他进程共享的驻留页）、Java 堆和原生堆等分类。排查泄漏还要结合对象引用、分配调用栈、`maps` / `smaps` 映射明细和业务对象的生命周期。

这组命令依次查看主进程汇总、指定子进程汇总和内核提供的 `smaps_rollup` 映射汇总。读取 `/proc/<pid>/smaps_rollup` 通常需要 `root` 权限、`userdebug` 系统镜像，或设备明确允许对应的 `/proc` 访问；量产设备返回 `Permission denied` 只表示当前调用者没有读取权限。

```bash
adb shell dumpsys meminfo com.example.app
adb shell dumpsys meminfo com.example.app:editor
editor_pid="$(adb shell pidof com.example.app:editor | tr -d '\r')"
adb shell su 0 cat "/proc/${editor_pid}/smaps_rollup"
```

`dumpsys meminfo` 各列与 `/proc` 中的 RSS/PSS 采用不同的采集和汇总方式，不能混入同一条时间序列。比较前应固定设备、系统版本、测试场景和采样工具；多进程应用还要分别记录应用进程、WebView 渲染进程和相关 GPU 内存。

预算值应来自目标设备上的实测峰值，并提前规定超限时允许降低哪些资源规格。表中列出了各进程需要记录的输入、资源释放时机和超限处理，不提供跨设备通用比例。

| 对象 | 需要单独测量 | 生命周期控制 | 超出预算后的动作 |
| --- | --- | --- | --- |
| 主进程 | Java 缓存内容的实测字节数；原生内存、图形内存与线程栈分别计数 | UI 隐藏或进入后台时释放可重建资源 | 缩小缓存、停止预取、降低后台并发 |
| 图片任务进程 | 输入尺寸、图层数、解码副本、Bitmap / `HardwareBuffer` | 任务完成后停止 `Service`、解除绑定并关闭句柄 | 降低分辨率、分块处理、限制并发任务 |
| WebView 宿主与渲染进程 | 页面数量、通过 `addJavascriptInterface()` 暴露给 JavaScript 的对象、渲染进程 PSS、GPU 使用量 | 页面销毁时移除引用；用渲染进程回调识别退出 | 取消非必要预热、减少并发页面、简化页面资源 |
| 批处理进程 | 单批对象、文件映射、原生缓冲区和序列化副本 | 每批关闭流与描述符；无任务时停止组件 | 缩小批大小、暂停后台任务；同一任务 ID 重试时不得重复写入结果 |

这张表的重点是给每个进程指定可观测的输入和明确的释放时机。没有这两项，单个“内存上限”无法说明是哪类分配增长，也无法判断任务完成后是否回收了可重建资源。

### 用进程状态信号释放可重建资源

Android 17 的 `onTrimMemory()` 实现应关注 `TRIM_MEMORY_UI_HIDDEN` 与 `TRIM_MEMORY_BACKGROUND`。从 Android 14（API 34）开始，系统不再投递 `TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE` 和 `TRIM_MEMORY_COMPLETE`；这些常量在 Android 15（API 35）废弃。`TRIM_MEMORY_UI_HIDDEN` 表示进程原先显示的 UI 已不可见，`TRIM_MEMORY_BACKGROUND` 表示进程进入按最近使用顺序维护的后台 LRU 列表。两者描述状态变化，并非连续的系统内存压力等级。低内存设备还要通过 `ActivityManager.isLowRamDevice()` 选择更小的资源规格。

`onLowMemory()` 从 API 34 起也不再调用，并于 API 35 废弃；最低支持版本高于 API 14 且已经实现 `onTrimMemory()` 的应用，可以把 `onLowMemory()` 留空。不要依赖这些旧回调处理 Android 17 的资源释放。

这段回调只释放可重建资源。`releaseUiOnlyResources()` 不应删除播放、导航或前台服务仍在使用的数据，`releaseRebuildableCaches()` 也不应关闭活跃任务占用的资源。

```kotlin
override fun onTrimMemory(level: Int) {
    if (level >= ComponentCallbacks2.TRIM_MEMORY_BACKGROUND) {
        releaseRebuildableCaches()
    }
    if (level >= ComponentCallbacks2.TRIM_MEMORY_UI_HIDDEN) {
        releaseUiOnlyResources()
    }
}
```

使用 `>=` 能兼容系统以后插入的中间等级。`BACKGROUND` 的数值高于 `UI_HIDDEN`，收到前者时两个分支都会执行，因此两个函数应释放不同资源，并保证重复调用不会重复关闭同一资源或产生错误。兼容 Android 13 及更早版本的实现可以保留旧等级处理，但 Android 17 不会发送这些旧等级。

### 把线程数纳入虚拟地址预算

线程栈会占用虚拟地址；其中已访问的页面还可能计入 RSS/PSS。Android 17 ART 的 `Thread::CreateNativeThread()` 先调用 `FixStackSize()`：默认请求改用运行时默认栈大小，然后加入兼容空间和栈溢出保护区，满足 POSIX 线程库规定的最小栈大小 `PTHREAD_STACK_MIN`，并向上进行页对齐。修正后的数值才会传给 `pthread_attr_setstacksize()` 和 `pthread_create()`，所以代码请求的栈大小不等于最终映射大小。

治理线程内存时应限制线程来源和最大并发：复用有界线程池，关闭不再使用的执行器（executor），并核对每个 SDK 创建的常驻线程。只有在调用深度可控，且递归、JNI、复杂解析与第三方库调用路径都经过压力测试时，才可以自行缩小栈；否则线程创建失败可能转化为 `StackOverflowError` 或原生代码崩溃。

具体修正规则可查阅 AOSP `android-17.0.0_r1` 的 [`art/runtime/thread.cc`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/thread.cc) 中 `FixStackSize()` 与 `Thread::CreateNativeThread()`。

### Android 17 应用内存限制

应用内存限制属于 Android 17 对所有应用生效的行为变更，不按 `targetSdkVersion` 区分，但只在部分设备启用。AOSP r1 的实现要求功能标志开启，设备提供 `/vendor/etc/memory-limiter-config.xml`，并且配置中至少有一组限制与 `/proc/meminfo` 的设备总内存 `MemTotal` 匹配。配置分别定义 `visible`（用户仍可感知）和 `not-visible`（用户不可见）进程的限制；同一进程可能在前台低于限制，进入后台后因限制降低而超限。

这套限制独立于 ART `memoryClass`、`largeHeap` 和 lmkd。原生层 `MemoryLimiter` 使用 Linux 控制组（cgroup）约束单个进程：它监听 `memory.events` 中 `memory.high` 计数的变化，把交换区上限写入 `memory.swap.max`，并用这个统计量判断是否超过 `AnonSwap` 限制：

> `memory.stat` 中的 `anon + shmem`，再加 `memory.swap.current`

其中 `anon` 是匿名页，`shmem` 是共享内存页，`memory.swap.current` 是该 cgroup 当前使用的交换空间。超过 `memory.high` 会促使内核回收页面并限制分配速度，`memory.swap.max` 则限制该 cgroup 可用的交换空间。`AnonSwap` 是源码为上述组合量使用的名称，与 PSS、RSS 或 Java 堆都不是同一个指标。

Android 17 r1 确认 `AnonSwap` 超限后，先把当前进程的 `memory.high` 和 `memory.swap.max` 恢复为 `max`，解除两项限制。相关剖析功能标志均开启且系统能取得包名时，系统再发送 `TRIGGER_TYPE_ANOMALY` 异常剖析触发器；无论是否成功生成剖析文件，源码都会延迟 30 秒请求终止进程。这 30 秒只为系统剖析器预留处理时间，不是应用可以依赖的保存期限，业务状态仍应在正常流程中持续保存。

退出归因应同时检查：

- `ApplicationExitInfo.getReason() == REASON_OTHER`；`ApplicationExitInfo` 是系统保存的历史进程退出记录；
- `getDescription()` 包含固定标记 `MemoryLimiter:AnonSwap`；
- 退出前的进程状态、测试场景、PSS/RSS 采样和系统触发的剖析文件能够对应到同一次事件。

`getPss()` / `getRss()` 可能返回零，也不保证记录的是终止瞬间；`getTraceInputStream()` 也不会固定附带 `MemoryLimiter` 的诊断文件。命中只能证明匿名页、共享内存页与交换空间的组合量超过设备策略，单凭这一条记录无法判定内存泄漏。大图处理、端侧模型推理、WebView 或音视频处理的短时峰值也可能触发限制。

> **版本警告**：这段历史脚本保留了原变量名 `TEST_LIMIT_MB`，但 `android-17.0.0_r1` 把数字解释为设备总 RAM 的百分比，并要求使用 1–99 的整数。运行 r1 时应把该变量设为测试百分比，忽略变量名和报错文字中的 `MB`。现行 Android 17 官方文档已经把数字改为 MB，并增加 `max`，两种语法不能混用。

这段脚本只展示“查询状态、施加测试限制、恢复默认限制”的顺序，应在专用测试设备上运行。r1 中传入的数值是根据场景基线选择的故障注入百分比，不是应用发布时的预算：

```bash
target_pid="$(adb shell pidof com.example.app:editor | tr -d '\r')"
test_limit_mb="${TEST_LIMIT_MB:?export TEST_LIMIT_MB to an integer MB value}"
adb shell am memory-limiter status
adb shell am memory-limiter manual "$target_pid" "$test_limit_mb"
adb shell am memory-limiter manual "$target_pid" none
```

在 r1 上，`manual` 的帮助文本为 `manual <PID> <PERCENT|none>`；现行官方文档则是 `manual <pid> <limit>|max|none`，其中 `limit` 的单位为 MB。测试前应查看目标系统构建的命令帮助和限制状态，不能只根据“Android 17”这个版本名推断参数单位。先用 `status` 保存设备是否启用及 `visible` / `not-visible` 配置，每次 `manual` 后再次查询状态，测试结束用 `none` 恢复设备默认限制。`ignore all` 会改变整台设备的限制策略，不能用于掩盖回归测试失败。

r1 的 Java 控制逻辑与命令解析见 [`MemoryLimiter.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java) 和 [`ActivityManagerShellCommand.java`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java)，cgroup 文件访问与 `AnonSwap` 公式见原生层 [`com_android_server_am_MemoryLimiter.cpp`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)。

## 64 位迁移与内存空间扩展

多进程改变内存分配的进程归属，64 位迁移扩大单个进程可用的虚拟地址范围，两者解决的问题不同。

Google Play 的 64 位要求适用于包含原生代码的应用。若继续分发某个 32 位 ABI，应为对应架构提供可工作的 64 位版本，例如 `armeabi-v7a` 对应 `arm64-v8a`、`x86` 对应 `x86_64`；在设备兼容性与分发策略允许时，也可以只提供 64 位 ABI。完全由 Java / Kotlin 编写、依赖中也没有原生库的应用，无需为了在 64 位设备上运行而添加原生库。

线程栈、`.so`、`.dex` / `.oat`、WebView、图形资源和原生缓冲区都会占用虚拟地址。32 位进程即使还有可用物理内存，也可能因为虚拟地址耗尽或找不到足够大的连续区间，导致 `mmap`、动态链接器或 `pthread_create` 失败。64 位进程提供了大得多的地址范围，但不会增加设备物理 RAM，也不会改变系统施加的应用内存限制。

64 位指针会增加部分原生对象、表结构和容器节点的体积；二进制大小、冷启动 I/O、指令缓存命中率和内存访问局部性也可能变化。JNI 代码不能把指针存入 `int` 或 `jint`，应使用 `uintptr_t`、`intptr_t` 或其他与指针宽度匹配的字段。ABI 迁移还要覆盖第三方 SDK、插件、热修复、动态加载路径、符号文件和原生崩溃调用栈解析。

迁移检查按这条顺序做：

- 安装包检查：用 APK Analyzer 或解包结果核对 ABI；每个受支持的 64 位环境都不能依赖只有 32 位版本的 `.so`。
- 运行时检查：用 `Process.is64Bit()` 确认当前进程位数；`Build.SUPPORTED_ABIS` 只表示设备支持 ABI 的优先顺序，不能证明当前进程已经以 64 位运行。
- 代码检查：排查指针截断、结构体布局、序列化格式、汇编、编译参数和按 ABI 选择资源的逻辑。
- 性能检查：在同一设备上对比启动耗时、PSS、原生堆、图形内存、线程数、缺页异常和崩溃率。
- 设备检查：至少覆盖 64 位进程、仍受支持的 32 位设备和仅支持 64 位的环境；仅支持 64 位的环境能直接暴露遗漏的 32 位专用依赖。

## 实战决策表

| 现象 | 优先判断 | 推荐动作 | 不建议动作 |
| --- | --- | --- | --- |
| Java 堆 OOM，GC 后仍无法分配对象 | `java.lang.OutOfMemoryError`、堆转储、`getMemoryClass()` | 按 [23.4 Java 堆优化策略](./04-java-heap-optimization.md) 检查对象和缓存；短时峰值可评估 `largeHeap` | 直接拆进程却不修改对象生命周期 |
| `pthread_create` 失败或 `maps` 显示虚拟地址碎片严重 | 线程数、`/proc/<pid>/maps`、32 / 64 位状态 | 限制线程池和常驻线程，迁移到 64 位 | 未经压力测试便统一缩小线程栈 |
| WebView / 图片编辑使主进程峰值过高 | 宿主进程、渲染进程、原生/图形内存、任务生命周期 | 数据边界清楚时拆进程；停止已完成任务的组件并关闭资源 | 把 `largeHeap` 当作 WebView 或图形内存方案 |
| 后台发生低内存终止 | Android Vitals、进程重要性、PSS、后台任务和缓存 | 响应状态回调，减少可重建缓存与后台并发，缩短组件活跃时间 | 提高 Java 堆上限或用常驻组件延长进程寿命 |
| Android 17 `MemoryLimiter` 命中 | `ApplicationExitInfo` 的退出原因与描述、`MemoryLimiter` 状态 | 定位匿名页、共享内存页或交换空间的异常增长，在目标设备复现并修复 | 把 `ignore all` 或 `max` 用作发布配置 |
| 低内存设备运行不稳 | `isLowRamDevice()`、ABI、RAM、zRAM、lmkd 日志 | 降低分辨率、批大小、缓存和并发数 | 沿用高内存设备的预算 |

同一现象可能对应多种限制，决策表的“优先判断”列用于选择第一组证据。确认 Java 堆、虚拟地址、系统内存压力或 `MemoryLimiter` 中的具体一类后，再执行对应动作，避免只因进程退出就统一增加堆上限。

## 小结

`largeHeap` 改变 ART Java 堆上限，多进程改变地址空间归属，64 位迁移扩大虚拟地址范围。诊断时要把 Java 堆 OOM、原生或图形内存增长、线程或映射失败、系统低内存终止，以及 Android 17 `MemoryLimiter` 命中分开处理。

预算应细化到每个进程、每类内存和具体场景。生命周期及 IPC 数据边界都清楚的高峰任务才适合拆进程；任务完成后停止组件并关闭资源，进程何时回收仍由系统决定。64 位可以缓解地址空间不足，却不会增加物理内存。方案变更后，应在同一设备和输入下复测 Java 堆、原生/图形内存、PSS、线程数、GC、退出原因和用户可见性能。

## 参考资料

- [Android 17：App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [Android 开发者博客：Android 17 内存效率建议](https://developer.android.com/blog/posts/prioritizing-memory-efficiency-essential-steps-for-android-17)
- [`<application android:largeHeap>`](https://developer.android.com/guide/topics/manifest/application-element#largeHeap)
- [`ActivityManager`：memory class API](https://developer.android.com/reference/android/app/ActivityManager)
- [Processes and threads overview](https://developer.android.com/guide/components/processes-and-threads)
- [Processes and app lifecycle](https://developer.android.com/guide/components/activities/process-lifecycle)
- [`TransactionTooLargeException`](https://developer.android.com/reference/android/os/TransactionTooLargeException)
- [`WebView` renderer process API](https://developer.android.com/reference/android/webkit/WebView)
- [`WebViewRenderProcess`](https://developer.android.com/reference/android/webkit/WebViewRenderProcess)
- [管理 WebView 对象](https://developer.android.com/develop/ui/views/layout/webapps/managing-webview)
- [Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [`ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Support 64-bit architectures](https://developer.android.com/google/play/requirements/64-bit)
- [AOSP `ActivityThread.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP `ActivityManager.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [AOSP `ComponentCallbacks2.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [AOSP ART `thread.cc` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/thread.cc)
- [AOSP `MemoryLimiter.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/MemoryLimiter.java)
- [AOSP `ActivityManagerShellCommand.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/java/com/android/server/am/ActivityManagerShellCommand.java)
- [AOSP `com_android_server_am_MemoryLimiter.cpp` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/services/core/jni/com_android_server_am_MemoryLimiter.cpp)
- [AOSP `TransactionTooLargeException.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/os/TransactionTooLargeException.java)
