---

title: "大内存与多进程策略"
chapter: "23.6"
section: "23.6"
status: finalized
applicable_versions: "Android 10 (API 29) - Android 16 (API 36)"
last_verified: "2026-06-08"
last_verified_against: "AOSP android-16.0.0_r1 + Android Developers ComponentCallbacks2 + Android Developers memory docs + Clippings/Android 性能优化"
confidence: medium
drafted_date: "2026-05-14"
polish_count: 0
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
    path: "frameworks/base/core/java/android/app/ActivityThread.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/app/ActivityManager.java @ android-16.0.0_r1"
  - type: aosp
    path: "frameworks/base/core/java/android/content/ComponentCallbacks2.java @ android-16.0.0_r1"
  - type: aosp
    path: "art/runtime/thread.cc @ android-16.0.0_r1"
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
task6_state: reviewed
task9_state: reviewed
task2b_state: fixed
reviewed_date: "2026-05-14"
reviewed_by: "openclaw-task6"
task6_result: pass-light-edit
task6_reviewed_date: "2026-05-14"
task6_review_notes: "2026-05-14 task6 review: L1/L2 轻修 11 处（术语格式、填充表达、维护成本表述）；四层质检通过，无新增 L3/L4 回炉项，送 Task9 技术复审。"
last_task6_review_log: "logs/review/2026-06-08-16-review.md"
last_task6_at: "2026-06-08T16:14:59+08:00"
last_task6_audit: "2026-06-08"
task9_result: auto-fixed
last_task9_at: "2026-06-08T10:20:00+08:00"
task9_reviewed_date: "2026-06-08"
task9_reviewed_by: "openclaw-task9"
last_task9_review_log: "logs/deep-review/2026-06-08-10-audit.md"
last_task9_audit: "2026-06-08"
last_task9_autofix_at: "2026-06-08"
task9_review_notes: "2026-06-08 Task9 idle audit：AUTO-FIX，补充 Android 14-16 onTrimMemory 等级边界，回到 Task6 复审。"
auto_finalized_by_task9: "2026-05-14T04:36:12+08:00"
task6_state: reviewed
last_task6_at: "2026-06-08T16:14:59+08:00"
last_task6_review_log: "logs/review/2026-06-08-16-review.md"
last_task6_audit: "2026-06-08"
deepseek_cn_review_state: done
last_deepseek_cn_review_at: 2026-06-15
---

# 大内存与多进程策略

<!-- outline-start -->
## 本节要点大纲

### 锚点（必须覆盖）

- 🔹 largeHeap 的使用场景与代价
- 🔹 多进程内存隔离与共享
- 🔹 进程内存预算管理
- 🔹 64 位迁移与内存空间扩展

### 扩展（可选深入）

- 🔸 （待扩展）

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->

## 为什么要了解大内存与多进程策略

大内存策略解决的是两个不同层面的限制：Java Heap 的增长上限，以及进程虚拟地址空间的可用范围。前者决定单进程内 Java 对象能申请到多少空间，后者决定 32 位进程还能不能继续 `mmap` 线程栈、`.so`、`.dex`、Bitmap、图形缓冲或匿名内存。

`android:largeHeap`、多进程和 64 位迁移经常被放在同一个讨论里，但它们的收益和代价不一样。`largeHeap` 扩大的是当前应用进程的 Dalvik / ART heap 增长上限；多进程把不同业务拆到多个 Linux 进程，各自拥有独立地址空间和运行时；64 位迁移把地址空间瓶颈从 32 位用户态的 GB 级抬到 TB 级。三者都可能降低 OOM 发生率，也都可能增加 PSS、启动耗时和维护成本。

实战里不要把它们当成“加内存开关”。先确认 OOM 类型，再决定手段：Java Heap OOM 优先回到 23.4 节处理对象和缓存；低内存杀进程优先看 4.4 节的 LMKD / oom_adj；32 位虚拟地址耗尽、线程栈过多、WebView / 图形 / Native 映射过大，才进入本篇的策略选择。

## largeHeap 的使用场景与代价

`android:largeHeap="true"` 声明在 `<application>` 上。官方文档的定义是：应用进程会以 large Dalvik heap 创建；该属性作用于应用创建的所有进程，但只对某个进程里第一个加载的应用生效。官方也明确提示，大多数 App 不该依赖它，开启后也不保证可用内存固定增加，因为设备总内存仍然会限制结果。[已验证: 官方文档, developer.android.com/guide/topics/manifest/application-element#largeHeap]

AOSP 的启动路径能解释这个属性的边界。`ActivityThread.handleBindApplication()` 在绑定应用时检查 `ApplicationInfo.FLAG_LARGE_HEAP`：命中后调用 `VMRuntime.getRuntime().clearGrowthLimit()`，否则调用 `clampGrowthLimit()`。`ActivityManager.getMemoryClass()` 读取 `dalvik.vm.heapgrowthlimit`，`getLargeMemoryClass()` 读取 `dalvik.vm.heapsize`。这说明 largeHeap 影响的是 ART heap 的 growth limit，不会让 Native heap、图形内存、线程栈或文件映射免费变小。[已验证: AOSP android-16.0.0_r1, frameworks/base/core/java/android/app/ActivityThread.java; frameworks/base/core/java/android/app/ActivityManager.java]

适合打开 largeHeap 的场景很少，通常要同时满足三个条件：

- 峰值来自短时 Java 对象或大数组，并且已经做过对象生命周期、缓存、Bitmap 和流式处理治理；如果主要增长来自 Native / Graphics / Stack，largeHeap 不会解决根因。
- 业务有明确的高内存窗口，例如大图编辑、离线地图切片、短时间批处理导入、复杂文档解析；长期常驻缓存不应借 largeHeap 扩大。
- 能按设备分层降级：低 RAM 设备、32 位进程、后台态或发热状态下，降低分辨率、批大小、并发数或缓存上限。

运行时先读取设备给出的上限，再按比例设预算。下面这段代码只用于确认当前进程可用的 Java Heap 级别，不能当成“还能分配多少内存”的实时值。

```kotlin
val am = context.getSystemService(ActivityManager::class.java)
val appInfo = context.applicationInfo
val heapClassMb = if ((appInfo.flags and ApplicationInfo.FLAG_LARGE_HEAP) != 0) {
    am.largeMemoryClass
} else {
    am.memoryClass
}

val javaCacheBudgetBytes = heapClassMb * 1024L * 1024L / 8L
```

这段预算把 Java 缓存控制在 heap class 的一小部分。比例要按业务压测调整：图片列表、播放器、地图和文档阅读器的缓存压力不同；后台进程还要主动收缩缓存，避免把前台进程推向低内存回收。

largeHeap 的代价主要有四类：

- GC 停顿风险变高：heap 上限扩大后，存活对象集合也可能变大；对象图越大，标记和移动成本越高。详见 23.4 节。
- 系统回收压力增加：PSS 上升后，LMKD 在内存压力下更容易杀缓存进程或低优先级进程。详见 4.4 节。
- 问题被延后暴露：泄漏、无界缓存和错误的批处理大小可能从“快速 OOM”变成“运行更久后卡顿或被杀”。
- 多进程口径更复杂：该属性作用于应用创建的所有进程，但共享 UID 或同进程加载多个应用时存在一致性要求，不能只按单个组件理解。

判断 largeHeap 是否有效，要看同一设备、同一场景、同一输入规模下的三组数据：Java Heap alloc / free、GC 次数与停顿、进程 PSS。只看 OOM 是否消失，容易把风险转移到系统内存压力上。[已验证: 官方文档, developer.android.com/reference/android/app/ActivityManager]

## 多进程内存隔离与共享

Android 默认让同一应用的组件运行在同一进程和主线程。组件可以通过 manifest 的 `android:process` 放到其他进程；远程 Binder 调用进入服务进程后，由系统维护的 Binder 线程池执行，服务端方法必须按并发调用设计。[已验证: 官方文档, developer.android.com/guide/components/processes-and-threads]

多进程的价值是隔离地址空间和故障域。大对象解析、WebView、地图、相机预览、图片编辑、插件运行时、短时批处理这类模块，放到子进程后可以在任务结束时退出整个进程，让 Java Heap、Native heap、线程栈、JIT 缓存、`.so` 映射和图形资源一起释放。对 32 位进程来说，这比在主进程里反复释放对象更干净，因为虚拟地址碎片也随进程退出消失。

多进程不会自动降低总内存。每个进程都会有独立的 ART 运行时、ClassLoader、线程、Binder 线程池、Native allocator 状态和业务缓存。`.so`、`.dex`、framework 代码页可以共享，脏页、Java 对象、线程栈和多数 Native 分配不能共享。官方文档对 PSS 的定义也说明了这一点：共享页按进程数量分摊，非共享页完整计入当前进程；RSS 统计更快，但会把共享页完整算进每个进程。[已验证: 官方文档, developer.android.com/topic/performance/memory-management]

适合拆进程的模块通常有这些特征：

- 峰值高且生命周期短：任务结束后能退出子进程，释放地址空间和脏页。
- 故障影响大：Native crash、WebView renderer 异常、插件崩溃不应带走主进程。
- 跨进程数据边界清晰：输入输出能压成文件路径、URI、句柄、任务 ID 或小型结果对象。
- 启动链路可控：子进程冷启动、ClassLoader 初始化、Provider 初始化不会拖慢用户路径。

不适合拆进程的模块也要明确：高频小调用、强共享内存状态、需要大量 Java 对象跨进程传输、每次都要同步 UI 状态的模块，拆出去后很容易把内存问题换成 Binder 成本、序列化成本和一致性问题。

一个可执行的拆分模板是“主进程只保留调度和轻量状态，子进程承载高峰值任务”。子进程启动后按任务 ID 拉取输入，产物写入文件或数据库，主进程只接收结果摘要。大数组和大 Bitmap 不走 Binder；跨进程传输大数据时优先用文件、`ContentProvider`、`ParcelFileDescriptor` 或共享内存句柄，并给句柄生命周期做归属记录。[已验证: 官方文档, developer.android.com/guide/components/processes-and-threads]

## 进程内存预算管理

预算要按“进程 × 内存类型 × 场景”拆开，不能只给 App 一个总数。主进程、WebView 进程、图片编辑进程、播放器进程的风险点不同：主进程怕常驻 PSS 和缓存；WebView 进程怕 renderer 峰值；图片编辑进程怕 Bitmap / Native / Graphics；播放器进程怕解码缓冲和 surface。

线下先用 `dumpsys meminfo` 建立基线，再补 Java heap dump、Native heap、Perfetto memory counter 或线上采样。`dumpsys meminfo` 的用途是确认 PSS / private dirty / heap alloc 等指标的组成；它不是泄漏归因工具，归因仍要回到对象、分配栈、maps / smaps 和业务生命周期。

```bash
adb shell dumpsys meminfo com.example.app
adb shell dumpsys meminfo com.example.app:editor
adb shell cat /proc/$(adb shell pidof com.example.app:editor)/smaps_rollup
```

这三条命令对应三个问题：主进程总账、子进程总账、指定进程的内核口径汇总。多进程场景下不要只看主进程，否则会漏掉子进程把系统内存推高的情况。

推荐把预算表写进发布检查，而不是停留在经验判断。

| 进程 | Java Heap 预算 | Native / Graphics 预算 | 退出策略 | 触发降级 |
| --- | --- | --- | --- | --- |
| 主进程 | 按 `memoryClass` 的固定比例给缓存 | 监控 Native heap 与 EGL / Graphic PSS | 不退出，只收缩缓存 | `onTrimMemory()`、后台、低 RAM |
| 图片编辑进程 | 按输入尺寸和图层数计算上限 | Bitmap / HardwareBuffer / 解码缓存单独计数 | 任务完成后退出或空闲超时退出 | 分辨率降级、分块处理 |
| WebView 进程 | 限制页面缓存和 JS bridge 对象 | renderer PSS、GPU 内存、磁盘缓存分开看 | 页面关闭后延迟回收 | 低端机禁用预热、减少并发页面 |
| 批处理进程 | 按批大小线性估算 | 文件 mmap、Native buffer 单独计数 | 每批结束释放，异常时杀进程重试 | 缩小批大小、暂停后台任务 |

预算的触发点要接系统信号。在本节适用范围内，Android 14-16（API 34-36）的 `onTrimMemory()` 实现应聚焦 `TRIM_MEMORY_UI_HIDDEN` 与 `TRIM_MEMORY_BACKGROUND`；`TRIM_MEMORY_RUNNING_LOW`、`TRIM_MEMORY_RUNNING_MODERATE`、`TRIM_MEMORY_RUNNING_CRITICAL`、`TRIM_MEMORY_MODERATE`、`TRIM_MEMORY_COMPLETE` 从 API 34 起不再投递，并在 API 35 被废弃。Android 13 及以下兼容代码可以保留旧等级分支。低 RAM 设备通过 `ActivityManager.isLowRamDevice()` 单独配置预算，不能沿用高端机阈值。[已验证: 官方文档, developer.android.com/topic/performance/memory; developer.android.com/reference/android/content/ComponentCallbacks2; AOSP android-16.0.0_r1, frameworks/base/core/java/android/content/ComponentCallbacks2.java]

线程栈也要进入虚拟内存预算。ART 在 `Thread::CreateNativeThread()` 路径里会修正线程栈大小，并通过 `pthread_attr_setstacksize()` 传给 `pthread_create()`；参考书把“线程数量 × 栈空间”作为 32 位虚拟内存压力来源，是一个适合落到治理清单里的观察点。工程上优先收敛线程池和野线程，谨慎改线程栈大小；栈缩小后要覆盖递归、JNI、复杂解析和三方库调用，避免把 OOM 变成 StackOverflowError 或 native crash。[已验证: AOSP android-16.0.0_r1, art/runtime/thread.cc]

## 64 位迁移与内存空间扩展

多进程和预算管理解决的是“怎么分”的问题，64 位迁移解决的是“地址空间够不够”的问题——两者常常需要一起评估。

64 位迁移对内存策略有两层影响。第一层是兼容要求：Google Play 要求发布的 App 支持 64 位架构；如果 App 或 SDK 包含 C/C++ native code，就要检查 APK / AAB 里的 ABI 目录，为每个支持的 32 位 ABI 提供对应 64 位 ABI，例如 `armeabi-v7a` 对应 `arm64-v8a`，`x86` 对应 `x86_64`。[已验证: 官方文档, developer.android.com/google/play/requirements/64-bit]

第二层是地址空间：64 位进程能显著降低 32 位虚拟地址耗尽导致的 mmap 失败。线程多、`.so` 多、`.dex` / `.oat` 映射多、WebView / 图形 / Native buffer 多的 App，在 32 位进程里可能还没耗尽物理内存就先耗尽连续虚拟地址；64 位迁移后，这类失败会少很多。

64 位不是免费扩容。指针宽度增加会放大部分对象、表结构和 Native 数据结构；`.so` 体积、冷启动 I/O、指令缓存和内存局部性也可能变化。只用 Java / Kotlin 的 App 通常已经能在 64 位设备上运行；包含 native code 的 App 要把 ABI、三方 SDK、插件、热修复、`.so` 加载路径、崩溃符号表和性能基线一起迁移。

迁移检查按这条顺序做：

- 包产物检查：AAB / APK 中是否包含 `lib/arm64-v8a`；如果还保留 `armeabi-v7a`，两边 `.so` 集合要能对应业务功能。
- 运行时检查：启动日志、`Build.SUPPORTED_ABIS`、native loader、插件 `.so` 搜索路径和灰度开关要能区分 32 / 64 位。
- 性能检查：同设备对比启动耗时、PSS、Native heap、Graphics、线程数、page fault 和崩溃率。
- 兜底检查：老设备、只支持 32 位的三方 SDK、厂商 ROM、WebView / Chromium 版本差异要保留降级路径。

对内存优化来说，优先级可以这样排：32 位虚拟地址 OOM 或 `pthread_create` / `mmap` 失败高发，优先推动 64 位和线程治理；单进程 Java Heap OOM 高发，优先处理对象生命周期、缓存和 largeHeap 边界；主进程常驻 PSS 高，优先拆预算和清理常驻资源；高峰值短任务高，优先评估子进程隔离。

## 实战决策表

| 现象 | 优先判断 | 推荐动作 | 不建议动作 |
| --- | --- | --- | --- |
| Java Heap OOM，GC 后仍无法分配对象 | `java.lang.OutOfMemoryError`、heap dump、`getMemoryClass()` | 回到 23.4 节治理对象和缓存；短时峰值可评估 largeHeap | 直接拆进程但不改对象生命周期 |
| `pthread_create` 失败或 maps 地址空间碎片严重 | 线程数、`/proc/<pid>/maps`、32 / 64 位状态 | 收敛线程池、减少常驻线程、推动 64 位 | 全局缩小线程栈且不做压测 |
| WebView / 图片编辑导致主进程峰值过高 | 子模块 PSS、Native / Graphics、任务生命周期 | 拆子进程，任务完成后释放或退出 | 把 largeHeap 当 WebView 内存方案 |
| 后台被系统杀 | oom_adj、PSS、后台任务、缓存大小 | 降低后台缓存，响应 `onTrimMemory()`，减少后台并发 | 提高 heap 上限或保活 |
| 低端机运行不稳 | `isLowRamDevice()`、ABI、RAM、zRAM、LMKD 日志 | 降级分辨率、批大小、缓存和并发数 | 沿用高端机预算 |

## 小结

大内存策略的安全顺序是：先定位 OOM 类型，再缩小对象和线程的常驻面，随后用多进程隔离高峰值任务，再评估 largeHeap。64 位迁移适合解决地址空间瓶颈，但不能替代预算管理。每一种方案都要用 PSS、Java Heap、Native / Graphics、线程数、GC 停顿和 LMKD 结果复测，避免把一个进程里的 OOM 转移成整机内存压力。
