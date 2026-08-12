---

title: "大内存与多进程策略"
chapter: "23.6"
section: "23.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 17 (API 37)"
last_verified: "2026-08-11"
last_verified_against: "AOSP android-17.0.0_r1 + Android Developers App Memory Limits / ComponentCallbacks2 / memory docs + Clippings/Android 性能优化"
confidence: medium
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
    path: "https://developer.android.com/reference/android/content/ComponentCallbacks2"
  - type: official
    path: "https://developer.android.com/google/play/requirements/64-bit"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java @ android-17.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java @ android-17.0.0_r1"
  - type: aosp
    path: "art/runtime/thread.cc @ android-17.0.0_r1"
  - type: official
    path: "https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits"
  - type: aosp
    path: "frameworks/base/services/core/java/com/android/server/am/MemoryLimiter.java @ android-17.0.0_r1"
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
pipeline_stage: ready-to-publish
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

大内存策略解决的是两个不同层面的限制：Java Heap 的增长上限，以及进程虚拟地址空间的可用范围。前者决定单进程内 Java 对象能申请到多少空间，后者决定 32 位进程还能不能继续 `mmap` 线程栈、`.so`、`.dex`、Bitmap、图形缓冲或匿名内存。

`android:largeHeap`、多进程和 64 位迁移作用在不同边界。`largeHeap` 扩展应用进程的 ART heap growth limit；多进程让组件拥有独立的地址空间和运行时，同时产生重复的进程级成本；64 位迁移扩大可用虚拟地址范围，也会改变指针和部分 native 数据结构的大小。任何一种手段都不能保证降低 PSS 或消除泄漏。

先确认失败类型，再选择手段：Java Heap OOM 回到 23.4 节检查对象与缓存；低内存杀进程看 4.4 节的 LMKD 与进程优先级；`pthread_create`、`mmap` 或 linker 失败需要同时检查线程数、映射布局、ABI 和资源限制。WebView、Graphics 或 Native 指标上涨，也要先确认具体分配方。

Android 17 还在部分设备上引入基于设备总 RAM 的 app memory limits，目标是限制极端泄漏和异常值。该机制适用于运行在 Android 17 上的应用，不受 `targetSdkVersion` 控制；是否启用以及限制状态需要从设备查询。`largeHeap` 或拆分进程都不能作为绕过系统内存约束的方案，退出识别与取证见本节后文。

## largeHeap 的使用场景与代价

`android:largeHeap="true"` 声明在 `<application>` 上。官方文档定义了三个边界：它作用于该应用创建的所有进程；同一进程只采用第一个被加载应用的设置；共享 UID 且共享进程的应用必须保持一致。设备可以让 large memory class 与普通 memory class 相同，因此开启属性不保证增加固定容量。

Android 17 的 `ActivityThread.handleBindApplication()` 检查 `ApplicationInfo.FLAG_LARGE_HEAP`：命中后调用 `VMRuntime.getRuntime().clearGrowthLimit()`，否则调用 `clampGrowthLimit()`。`ActivityManager.getMemoryClass()` 读取 `dalvik.vm.heapgrowthlimit`，`getLargeMemoryClass()` 读取 `dalvik.vm.heapsize`。这些路径只改变 ART heap 限制，不会降低 Native Heap、Graphics、线程栈或文件映射。

[源码锚点: AOSP `android-17.0.0_r1`, `frameworks/base/core/java/android/app/ActivityThread.java`, `frameworks/base/core/java/android/app/ActivityManager.java`]

适合打开 largeHeap 的场景很少，通常要同时满足三个条件：

- 峰值来自短时 Java 对象或大数组，并且已经做过对象生命周期、缓存、Bitmap 和流式处理治理；如果主要增长来自 Native / Graphics / Stack，largeHeap 不会解决根因。
- 业务有明确的高内存窗口，例如大图编辑、离线地图切片、批处理导入或复杂文档解析；长期常驻缓存不应借 largeHeap 扩大。
- 能按设备分层降级：低 RAM 设备、32 位进程、后台态或发热状态下，降低分辨率、批大小、并发数或缓存上限。

下面的函数读取设备提供的普通/large memory class、当前进程的 `Runtime.maxMemory()` 和 low-RAM 标记。这些值是制定策略的输入，不等于此刻还能成功分配的字节数。

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

缓存预算还要结合对象实测大小、并发峰值、重建成本、前后台状态和其他内存类型，不能由 memory class 乘一个通用比例得出。`Runtime.maxMemory()` 只描述当前 ART heap 上限；Native 与 Graphics 仍需单独测量。

largeHeap 的代价主要有四类：

- GC 成本可能增加：largeHeap 本身不会创建对象；应用若用新增空间保留更多对象，标记、复制或压缩的工作量才会随 live set 增长。详见 23.4 节。
- 系统回收压力增加：PSS 上升后，LMKD 在内存压力下更容易杀缓存进程或低优先级进程。详见 4.4 节。
- 问题被延后暴露：泄漏、无界缓存和错误的批处理大小可能从“快速 OOM”变成“运行更久后卡顿或被杀”。
- 多进程口径更复杂：该属性作用于应用创建的所有进程，但共享 UID 或同进程加载多个应用时存在一致性要求，不能只按单个组件理解。

判断 largeHeap 是否有效，要在同一设备、场景和输入下比较 Java Heap 存活量、分配与 GC、进程 PSS/RSS，以及 Android 17 的退出原因。只看 OOM 是否消失，可能把风险转移到系统内存压力上。

## 多进程内存隔离与共享

Android 默认让同一应用的组件运行在同一进程和主线程。组件可以通过 manifest 的 `android:process` 放到其他进程；远程 Binder 调用进入服务进程后，由系统维护的 Binder 线程池执行，服务端方法必须按并发调用设计。

多进程的主要价值是隔离地址空间、组件生命周期与故障域。图片编辑、插件运行时或边界清楚的批处理服务放到独立进程后，系统回收该进程时会一并释放 Java Heap、Native Heap、线程栈、JIT cache 和映射。应用不能把“主动杀子进程”当作正常资源释放 API：Android 进程生命周期由系统根据活动组件和重要性管理，任务结束时应停止 Service、解除绑定并持久化结果，让组件状态准确反映进程是否仍有工作。

多进程不会自动降低总内存。每个进程都会有独立的 ART 运行时、ClassLoader、线程、Binder 线程池、Native allocator 状态和业务缓存。`.so`、`.dex`、framework 代码页可以共享，脏页、Java 对象、线程栈和多数 Native 分配不能共享。官方文档对 PSS 的定义也说明了这一点：共享页按进程数量分摊，非共享页完整计入当前进程；RSS 统计更快，但会把共享页完整算进每个进程。

适合拆进程的模块通常有这些特征：

- 峰值高且生命周期清楚：任务完成后没有继续存活的组件或绑定关系，系统可以把该进程转为 cached 并在需要时回收。
- 故障影响大：Native crash、WebView renderer 异常、插件崩溃不应带走主进程。
- 跨进程数据边界清晰：输入输出能压成文件路径、URI、句柄、任务 ID 或小型结果对象。
- 启动链路可控：子进程冷启动、ClassLoader 初始化和在该进程运行的 ContentProvider 初始化已经纳入目标路径测量。

不适合拆进程的模块也要明确：高频小调用、强共享内存状态、需要大量 Java 对象跨进程传输、每次都要同步 UI 状态的模块，拆出去后很容易把内存问题换成 Binder 成本、序列化成本和一致性问题。

一个可执行的拆分模板是“主进程保留调度与轻量状态，独立进程处理边界明确的任务”。服务按任务 ID 读取输入，把产物写入文件或数据库，Binder 只返回状态与结果引用。Binder transaction buffer 当前是每个进程固定的 1 MB，并由该进程所有进行中的 transaction 共享；单次参数不大也可能在并发 transaction 下触发 `TransactionTooLargeException`。因此，大数组和 Bitmap 不应直接放进 Parcel。

大数据可以通过 `ContentProvider`、`ParcelFileDescriptor`、文件或 `SharedMemory` 传递句柄，并明确关闭时机、访问权限与并发读写协议。句柄方案减少 Parcel payload，不代表数据没有内存和 I/O 成本。

WebView 还要单独说明：从 Android 8.0（API 26）起，WebView 可以在多进程模式下使用沙箱化 renderer。把承载 WebView 的 Activity 再放入应用自定义进程，会增加一个应用进程，但不等于合并或替代 renderer。是否存在关联 renderer 可通过 `WebView.getWebViewRenderProcess()` 检查；测量时要区分宿主进程、renderer、GPU 与主进程。

## 进程内存预算管理

预算要按“进程 × 内存类型 × 场景”拆开，不能只给 App 一个总数。主进程、WebView 进程、图片编辑进程、播放器进程的风险点不同：主进程怕常驻 PSS 和缓存；WebView 进程怕 renderer 峰值；图片编辑进程怕 Bitmap / Native / Graphics；播放器进程怕解码缓冲和 surface。

线下先用 `dumpsys meminfo` 建立基线，再补 Java heap dump、Native heap、Perfetto memory counter 或线上采样。`dumpsys meminfo` 用于查看 PSS、private dirty、Java/Native heap 等分类；泄漏归因仍要回到对象引用、分配栈、`maps` / `smaps` 和业务生命周期。

下面三条命令分别查看主进程总账、指定子进程总账和内核的 `smaps_rollup` 汇总。第三条通常需要 root、userdebug 环境或设备允许相应的 `/proc` 访问，普通量产设备上出现 `Permission denied` 不代表进程没有该映射。

```bash
adb shell dumpsys meminfo com.example.app
adb shell dumpsys meminfo com.example.app:editor
editor_pid="$(adb shell pidof com.example.app:editor | tr -d '\r')"
adb shell su 0 cat "/proc/${editor_pid}/smaps_rollup"
```

`dumpsys meminfo` 的各列和 `/proc` 的 RSS/PSS 口径不能直接混成一条时间序列。固定设备、版本、场景和采样工具后再比较；多进程应用还要把应用进程、WebView renderer 和相关 GPU 开销分开记录。

预算值应来自目标设备上的实测峰值和可接受的降级结果。下表给出各进程需要记录的输入、退出条件和降级动作，不给跨设备通用比例。

| 对象 | 需要单独测量 | 生命周期控制 | 超出预算后的动作 |
| --- | --- | --- | --- |
| 主进程 | Java 缓存的实测 payload；Native、Graphics 与线程栈分别计数 | UI 隐藏或进入后台时释放可重建资源 | 缩小缓存、停止预取、降低后台并发 |
| 图片任务进程 | 输入尺寸、图层数、解码副本、Bitmap / HardwareBuffer | 任务完成后停止 Service、解除绑定并关闭句柄 | 降低分辨率、分块处理、限制并发任务 |
| WebView 宿主与 renderer | 页面数量、JS bridge 持有对象、renderer PSS、GPU 使用 | 页面销毁时移除引用；用 renderer 回调识别退出 | 禁用不必要的预热、减少并发页面、简化页面资源 |
| 批处理进程 | 单批对象、文件映射、Native buffer 和序列化副本 | 每批关闭流与描述符；无任务时停止组件 | 缩小批大小、暂停后台任务、按任务 ID 幂等重试 |

### 用进程状态信号释放可重建资源

Android 17 的 `onTrimMemory()` 实现应聚焦 `TRIM_MEMORY_UI_HIDDEN` 与 `TRIM_MEMORY_BACKGROUND`。从 Android 14（API 34）开始，系统不再投递 `TRIM_MEMORY_RUNNING_*`、`TRIM_MEMORY_MODERATE` 和 `TRIM_MEMORY_COMPLETE`；这些常量在 Android 15（API 35）正式废弃。前两个信号描述 UI 可见性和进程进入后台 LRU 的状态，不是连续的系统内存压力刻度。低 RAM 设备还要通过 `ActivityManager.isLowRamDevice()` 单独选择资源规格。

下面的回调只释放可重建资源。`releaseUiOnlyResources()` 不应清掉仍在播放、导航或前台服务使用的数据，`releaseRebuildableCaches()` 也不应关闭仍被活跃任务占用的资源。

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

使用 `>=` 可以容纳未来插入的中间等级。`BACKGROUND` 的数值更高，此时两个分支都会执行，因此两个释放函数需要职责分离并保持幂等。Android 13 及以下的兼容实现可以保留旧等级逻辑，但不要期待这些等级在 Android 17 上出现。

### 把线程数纳入虚拟地址预算

线程栈既占虚拟地址，也可能按实际触页量进入 RSS/PSS。Android 17 ART 的 `Thread::CreateNativeThread()` 会先调用 `FixStackSize()`：默认请求会换成运行时默认值，随后加入兼容空间、栈溢出保护区，满足 `PTHREAD_STACK_MIN`，并向上对齐到页大小；修正后的值再交给 `pthread_attr_setstacksize()` 和 `pthread_create()`。因此，代码传入的 stack size 不等于最终映射大小。

工程治理应先限制线程来源和最大并发：复用有界线程池，关闭不再使用的 executor，排查每个 SDK 的常驻线程。自行缩小栈只适用于调用深度可控且已经覆盖递归、JNI、复杂解析与第三方库路径的场景，否则可能把线程创建失败换成 `StackOverflowError` 或 native crash。

[源码锚点: AOSP `android-17.0.0_r1`, `art/runtime/thread.cc`, `FixStackSize()` 与 `Thread::CreateNativeThread()`]

### Android 17 App Memory Limits

App Memory Limits 属于 Android 17 对所有应用生效的行为变更，不按 `targetSdkVersion` 判断，但只在部分设备启用。AOSP r1 要求功能标志开启、存在 `/vendor/etc/memory-limiter-config.xml`，并能按设备 `MemTotal` 匹配至少一组配置。配置分别给 visible 与 not-visible 进程设置限制；同一进程前台正常、进入后台后命中限制并不矛盾。

它与 ART `memoryClass`、`largeHeap` 和 LMKD 不是同一套约束。native `MemoryLimiter` 监视 cgroup `memory.high` 事件，并用下面的量判断是否超限：

> `memory.stat` 中的 `anon + shmem`，再加 `memory.swap.current`

源码把它称为 `AnonSwap`。`memory.high` 负责节流和直接回收，`memory.swap.max` 限制该 cgroup 的匿名页继续换出；最终 profiling 与终止决定由 Android 用户空间完成。`AnonSwap` 不是 PSS、RSS 或 Java Heap 的别名。

Android 17 r1 超限后会先解除当前 `memory.high` / `memory.swap.max`，条件满足时发送 `TRIGGER_TYPE_ANOMALY`，再延迟发出终止请求，为 profiler 留出处理时间。源码中的延迟常量不是应用可依赖的宽限期，业务状态仍要在正常流程中持续保存。

退出归因应同时检查：

- `ApplicationExitInfo.getReason() == REASON_OTHER`；
- `getDescription()` 包含稳定 token `MemoryLimiter:AnonSwap`；
- 退出前进程状态、场景、PSS/RSS 最近采样与 anomaly profile 能关联到同一事件。

`getPss()` / `getRss()` 可能为零，也不保证是终止瞬间数值；`getTraceInputStream()` 也不是 MemoryLimiter 的固定附件。命中只能证明匿名页、共享内存与 swap 的组合超过设备策略，不能单独证明泄漏。大图处理、AI 推理、WebView 或音视频峰值同样可能触发。

下面的命令用于专用测试设备。`TEST_LIMIT_MB` 是根据当前场景基线选择的故障注入值，不是线上预算：

```bash
target_pid="$(adb shell pidof com.example.app:editor | tr -d '\r')"
test_limit_mb="${TEST_LIMIT_MB:?export TEST_LIMIT_MB to an integer MB value}"
adb shell am memory-limiter status
adb shell am memory-limiter manual "$target_pid" "$test_limit_mb"
adb shell am memory-limiter manual "$target_pid" none
```

先用 `status` 保存设备是否启用以及 visible / not-visible 配置；每次 `manual` 后重新查询状态，测试结束恢复 `none`。`android-17.0.0_r1` 的 shell parser 只接受整数与 `none`，针对该 tag 的脚本不发送较新文档中出现的 `max`。`ignore all` 会改变整机策略，也不应用来掩盖回归失败。

## 64 位迁移与内存空间扩展

多进程改变分配所属的进程，64 位迁移扩大单进程可用的虚拟地址范围，两者需要分别判断。

Google Play 的 64 位要求针对包含 native code 的应用。若继续分发某个 32 位 ABI，应为对应架构提供可工作的 64 位版本，例如 `armeabi-v7a` 对应 `arm64-v8a`、`x86` 对应 `x86_64`；也可以在设备兼容性与分发策略允许时只提供 64 位 ABI。纯 Java / Kotlin 应用及其纯 Java / Kotlin 依赖无需添加 native 库，就能运行在 64 位设备上。

线程、`.so`、`.dex` / `.oat`、WebView、图形资源和 Native buffer 都要占用虚拟地址。32 位进程可能在物理内存尚未耗尽时因为地址空间不足或找不到合适的连续区间而让 `mmap`、linker 或 `pthread_create` 失败。64 位进程显著放宽这一限制，但不增加设备物理 RAM，也不改变系统对应用施加的内存限制。

指针变宽会增加部分 Native 对象、表结构和容器节点的体积；二进制大小、冷启动 I/O、指令缓存和局部性也可能改变。JNI 代码不能把指针存入 `int` 或 `jint`，需要使用 `uintptr_t`、`intptr_t` 或与指针宽度匹配的字段。ABI 迁移还要覆盖第三方 SDK、插件、热修复、动态加载路径、符号文件和 Native 崩溃回溯。

迁移检查按这条顺序做：

- 包产物检查：用 APK Analyzer 或解包结果核对 ABI；每个要支持的 64 位环境都不能依赖仅有 32 位版本的 `.so`。
- 运行时检查：用 `Process.is64Bit()` 确认当前进程位数；`Build.SUPPORTED_ABIS` 表示设备支持的 ABI 顺序，不能单独证明当前进程是 64 位。
- 代码检查：排查指针截断、结构体布局、序列化格式、汇编、编译参数和按 ABI 选择资源的逻辑。
- 性能检查：同设备对比启动耗时、PSS、Native heap、Graphics、线程数、page fault 和崩溃率。
- 设备检查：至少覆盖 64 位进程、仍需支持的 32 位设备和 64 位-only 环境；后者最容易暴露遗漏的 32 位-only 依赖。

## 实战决策表

| 现象 | 优先判断 | 推荐动作 | 不建议动作 |
| --- | --- | --- | --- |
| Java Heap OOM，GC 后仍无法分配对象 | `java.lang.OutOfMemoryError`、heap dump、`getMemoryClass()` | 回到 23.4 节治理对象和缓存；短时峰值可评估 largeHeap | 直接拆进程但不改对象生命周期 |
| `pthread_create` 失败或 maps 地址空间碎片严重 | 线程数、`/proc/<pid>/maps`、32 / 64 位状态 | 收敛线程池、减少常驻线程、推动 64 位 | 全局缩小线程栈且不做压测 |
| WebView / 图片编辑导致主进程峰值过高 | 宿主进程、renderer、Native / Graphics、任务生命周期 | 边界清楚时拆进程；停止已完成任务的组件并关闭资源 | 把 largeHeap 当作 WebView 或 Graphics 内存方案 |
| 后台发生 LMK | Android Vitals、进程重要性、PSS、后台任务和缓存 | 响应状态回调，降低可重建缓存与后台并发，缩短组件活跃时间 | 提高 heap 上限或用常驻组件保活 |
| Android 17 Memory Limiter 命中 | `ApplicationExitInfo` 的 reason 与 description、limiter status | 定位匿名内存或 swap 异常增长，在目标设备复现并修复 | 用 `ignore all` 或 `max` 作为发布方案 |
| 低端机运行不稳 | `isLowRamDevice()`、ABI、RAM、zRAM、LMKD 日志 | 降级分辨率、批大小、缓存和并发数 | 沿用高端机预算 |

## 小结

`largeHeap`、多进程和 64 位分别改变 ART heap 上限、地址空间归属和虚拟地址范围。选型前要区分 Java Heap OOM、Native / Graphics 增长、线程或映射失败、LMK 与 Android 17 Memory Limiter 命中。

预算必须落实到每个进程、每种内存和具体场景。高峰任务只有在生命周期与 IPC 边界清楚时才适合拆进程；任务结束后停止组件并关闭资源，进程何时被回收仍由系统决定。64 位能缓解地址空间不足，不能增加物理内存或代替泄漏治理。所有方案都要在同一设备和输入下复测 Java Heap、Native / Graphics、PSS、线程、GC、退出原因与用户可见性能。

## 参考资料

- [Android 17：App memory limits](https://developer.android.com/about/versions/17/behavior-changes-all#app-memory-limits)
- [`<application android:largeHeap>`](https://developer.android.com/guide/topics/manifest/application-element#largeHeap)
- [`ActivityManager`：memory class API](https://developer.android.com/reference/android/app/ActivityManager)
- [Processes and threads overview](https://developer.android.com/guide/components/processes-and-threads)
- [Processes and app lifecycle](https://developer.android.com/guide/components/activities/process-lifecycle)
- [`TransactionTooLargeException`](https://developer.android.com/reference/android/os/TransactionTooLargeException)
- [`WebView` renderer process API](https://developer.android.com/reference/android/webkit/WebView)
- [`WebViewRenderProcess`](https://developer.android.com/reference/android/webkit/WebViewRenderProcess)
- [Manage your app's memory](https://developer.android.com/topic/performance/memory)
- [`ComponentCallbacks2`](https://developer.android.com/reference/android/content/ComponentCallbacks2)
- [Support 64-bit architectures](https://developer.android.com/google/play/requirements/64-bit)
- [AOSP `ActivityThread.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityThread.java)
- [AOSP `ActivityManager.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/app/ActivityManager.java)
- [AOSP `ComponentCallbacks2.java` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/frameworks/base/+/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [AOSP ART `thread.cc` @ `android-17.0.0_r1`](https://android.googlesource.com/platform/art/+/android-17.0.0_r1/runtime/thread.cc)
