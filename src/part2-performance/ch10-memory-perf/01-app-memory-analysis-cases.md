---
title: App 内存分析与案例
chapter: '10.1'
applicable_versions: Android 8.0 (API 26) - Android 17 (API 37)
last_verified: '2026-08-26'
last_verified_against: AOSP android-17.0.0_r1 / kernel android17-6.18-2026-06_r6; Android Developers memory/profiling/trim docs and Perfetto heapprofd docs checked 2026-08-26
confidence: medium
sources:
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java
- type: aosp
  path: https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java
- type: aosp
  path: https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/libpsi/psi.cpp
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/libpsi/include/psi/psi.h
- type: aosp
  path: https://android.googlesource.com/platform/system/memory/libmeminfo/+/refs/tags/android-17.0.0_r1/include/meminfo/procmeminfo.h
- type: kernel
  path: https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/psi.c
- type: blog
  path: https://juejin.cn/post/7677254638325727242
  note: Android PSI libpsi 源码解析
- type: official
  path: https://developer.android.com/topic/performance/memory-management
- type: official
  path: https://developer.android.com/studio/profile/capture-heap-dump
- type: official
  path: https://perfetto.dev/docs/data-sources/native-heap-profiler
- type: official
  path: https://developer.android.com/ndk/guides/memory-debug
- type: official
  path: https://developer.android.com/ndk/guides/wrap-script
- type: official
  path: https://developer.android.com/guide/practices/page-sizes
- type: blog
  path: Personal-Knowlodge/source/Android-Jank-Due-To-Low-Memory.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-08_wechat_谁动了我的内存_揭秘_OOM_崩溃下降_90_的秘密_1.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-06_wechat_抖音renderD128系统级疑难OOM分析与解决.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-08_wechat_MemoryThrashing_抖音直播解决内存抖动实践_1.md
- type: blog
  path: Personal-Knowlodge/source/2026-03-09_wechat_字节跳动应用性能监控帮助客户Java_OOM崩溃率下降80.md
- type: official
  path: https://developer.android.com/topic/performance/memory
  note: Android 内存管理官方指南
- type: official
  path: https://source.android.com/docs/core/perf/lmkd
  note: userspace lmkd 与 PSI / vmpressure 机制
- type: aosp
  path: frameworks/base/core/java/android/content/ComponentCallbacks2.java
- type: aosp
  path: frameworks/base/core/java/android/util/LruCache.java@android-17.0.0_r1
- type: official
  path: https://developer.android.com/reference/android/util/LruCache
- type: official
  path: https://developer.android.com/reference/android/content/ComponentCallbacks2
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingManager
- type: official
  path: https://developer.android.com/reference/android/os/ProfilingTrigger
- type: aosp
  path: frameworks/base/libs/hwui/RenderProperties.h
- type: aosp
  path: frameworks/base/libs/hwui/RenderNode.cpp
- type: aosp
  path: packages/modules/Profiling/framework/java/android/os/ProfilingTrigger.java
- type: aosp
  path: system/memory/lmkd/lmkd.cpp
- type: kernel
  path: mm/vmscan.c@android17-6.18-2026-06_r6
- type: kernel
  path: include/trace/events/vmscan.h@android17-6.18-2026-06_r6
tags:
- memory
- pss
- rss
- mat
- heapprofd
- memtrack
- memory-analysis
- case-study
- memory-leak
- native-memory
- low-memory
- oom
- cache
- gc
related_chapters:
- '4.1'
- '4.2'
- '4.4'
- '14.1'
- '15.3'
- '10.2'
- '10.3'
task6_state: reviewed
section: '10.1'
status: finalized
pipeline_stage: ready-to-publish
task2b_state: fixed
task9_state: reviewed
last_consolidated_at: '2026-08-24'
consolidated_from:
- src/part2-performance/ch10-memory-perf/01-app-memory-analysis.md
- src/part2-performance/ch10-memory-perf/05-case-studies.md
- src/part2-performance/ch10-memory-perf/02-memory-leak-growth.md
- src/part2-performance/ch10-memory-perf/03-memory-growth.md
last_body_apply_at: '2026-08-26T19:20:50+08:00'
last_body_apply_run_id: 20260826-191540-e0aa0648
last_review_finalize_at: '2026-08-26T20:23:27+08:00'
last_review_finalize_run_id: 20260826-201101-4eb9807b
---

# App 内存分析与案例

一条内存曲线只能说明某个统计口径发生了变化。Java heap（ART 管理的 Java/Kotlin 对象堆）、native allocator（C/C++ 默认内存分配器）、RSS、PSS、SwapPss、DMA-BUF（设备间共享缓冲区）和 GPU private memory（GPU 私有分配）分别观察不同对象；数值来自不同采样时刻时，直接相加都可能失真。

本文按 Android 17 / API 37 的 `android-17.0.0_r1` 核对平台行为，涉及 PSI 的内核实现以 `android17-6.18-2026-06_r6` 为准。分析顺序是先确定指标，再定位内存域，随后用对应工具寻找 owner（内存持有者或归属方）和生命周期。

## 内存域、基线与增长分类

### 1. 先确定问题属于哪种内存

#### 1.1 常用指标的含义

| 指标 | 主要来源 | 回答的问题 | 容易误用的地方 |
|---|---|---|---|
| Java heap used | ART / `Runtime` / heap dump | 当前 Java/Kotlin 对象占用与引用关系 | 当成整个进程内存 |
| Java heap max | `Runtime.maxMemory()`、`getMemoryClass()` | Java heap 的增长预算 | 与 PSS 或 Graphics 直接相除 |
| Native allocated | bionic allocator / `Debug.getNativeHeapAllocatedSize()` | 分配器仍记为已分配的字节 | 当成 native RSS |
| RSS（Resident Set Size，驻留集大小） | `/proc/<pid>/status`、smaps | 当前驻留在物理内存中的共享页与私有页总和 | 汇总多个进程时重复计算共享页 |
| PSS（Proportional Set Size，按比例分摊集） | smaps / smaps_rollup | 私有页加按映射进程数分摊的共享页 | 当成硬上限或 LMKD 唯一依据 |
| USS（Unique Set Size，独占集大小） | Private Clean + Private Dirty | 当前进程独占的页面 | 忽略 swap、GPU private 与未映射 DMA-BUF |
| SwapPss | smaps | 按映射进程数分摊的换出页面 | 与 resident PSS（仍驻留部分）使用不同采样时刻相加 |
| Graphics / memtrack | `IMemtrack` 与厂商 HAL（硬件抽象层） | smaps 难以覆盖的图形、GL 和 GPU 私有内存 | 假定所有设备记账完整一致 |

PSS 适合比较包含共享映射的进程内存占用，RSS 适合低成本观察驻留变化。两者都受共享库、文件页、ZRAM（内存压缩交换设备）、进程状态和采样时刻影响。

`ActivityManager.getMemoryClass()` 与 `getLargeMemoryClass()` 返回 MB，描述 Dalvik/ART heap 的近似预算。PSS 以 kB 报告，并包含 Java heap 之外的原生分配、代码页、线程栈、图形内存和系统共享页分摊。二者没有可直接计算的“PSS 使用率”。

#### 1.2 Android 17 的 `Debug.MemoryInfo`

`Debug.MemoryInfo` 将统计分成 dalvik（ART 托管堆）、native（原生分配）和 other（其他映射），并提供 Java Heap、Native Heap、Code、Stack、Graphics、Private Other、System、Total PSS 与 Total Swap 摘要。公开字段和摘要值以 kB 为单位。

几个边界需要保留：

- `getTotalPss()` 包含 swapped-out PSS，即按比例分摊的已换出页面；
- `getTotalUss()` 由各域 Private Clean 与 Private Dirty 相加；
- `getMemoryStats()` 的分类沿用 `dumpsys meminfo` 的 App Summary（应用摘要）口径；
- `Debug.getMemoryInfo()` 直接读取本进程底层统计，源码注明可能看不到部分受保护的 graphics 分配；
- `ActivityManager.getProcessMemoryInfo()` 可以补充系统侧统计，但 Android 10 / API 29 起只返回调用 UID 的进程，而且高频调用会得到缓存结果。

源码核对：

- [`Debug.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/os/Debug.java)
- [`ActivityManager.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ActivityManager.java#5115)

### 2. 建立第一份内存快照

下面的命令用于记录同一实验阶段的进程摘要、内存页大小和进程状态：

```bash
adb shell dumpsys meminfo -d com.example.app
adb shell getconf PAGE_SIZE
adb shell 'pid=$(pidof com.example.app); grep -E "VmRSS|RssAnon|RssFile|RssShmem|VmSwap|Threads" /proc/$pid/status'
adb shell dumpsys SurfaceFlinger --list
```

`dumpsys meminfo` 的详细列会随平台和厂商实现变化，报告中应保存原始输出。`/proc/<pid>/status` 的 `VmRSS` 是低成本估计；Android 17 `libmeminfo` 的源码也注明它不如 smaps（逐映射内存统计）精确。SurfaceFlinger layer（图层）列表只用于核对可见图形对象，不能单独给出每个图层的 GPU 内存。

应用内若要取得一次自进程快照，可以使用公开 `ActivityManager` API：

```kotlin
data class AppMemorySnapshot(
    val totalPssKb: Int,
    val javaHeapKb: Int,
    val nativeHeapKb: Int,
    val graphicsKb: Int?,
    val javaUsedBytes: Long,
    val javaMaxBytes: Long,
    val nativeAllocatedBytes: Long,
)

fun captureAppMemory(
    activityManager: ActivityManager,
): AppMemorySnapshot {
    val info = activityManager
        .getProcessMemoryInfo(intArrayOf(Process.myPid()))
        .single()
    val stats = info.memoryStats
    val runtime = Runtime.getRuntime()

    return AppMemorySnapshot(
        totalPssKb = info.totalPss,
        javaHeapKb = stats.getValue("summary.java-heap").toInt(),
        nativeHeapKb = stats.getValue("summary.native-heap").toInt(),
        graphicsKb = stats["summary.graphics"]?.toIntOrNull(),
        javaUsedBytes = runtime.totalMemory() - runtime.freeMemory(),
        javaMaxBytes = runtime.maxMemory(),
        nativeAllocatedBytes = Debug.getNativeHeapAllocatedSize(),
    )
}
```

这个函数保留了 kB 与 byte 的单位后缀，避免混算。系统会限制 `getProcessMemoryInfo()` 的采样频率，不能把它放进每帧回调、紧循环或高频定时器；它适合在实验步骤边界调用，或由低频诊断任务触发。

### 3. Java/Kotlin heap：用引用关系证明泄漏

Heap dump 是某一时刻 Java/Kotlin 堆中可达对象图的快照。它能回答对象由谁引用、哪个对象支配一片子图，却不能解释 native `mmap`（原生内存映射）、GPU allocation（GPU 分配）或系统为何杀进程。

#### 3.1 三个必须分清的概念

- **Shallow Size**：对象自身在 managed heap（由 ART 管理的堆）中占用的字节，不含被引用对象；
- **Retained Size**：对象不可达后，预计可随它一起回收的受支配对象总量；
- **GC Root path**：对象通向 GC Root 的引用路径；GC Root 是垃圾回收器判定对象仍可达的起点，例如活跃线程、JNI global reference（JNI 全局引用）、类对象、系统类或活跃栈。

对象头、对齐、压缩引用和 ART 实现会改变 shallow size。不要用“两个 `int` 字段固定占多少字节”推导跨设备结论。

#### 3.2 可复现的泄漏检查

1. 固定初始页面和进程状态；
2. 执行同一生命周期动作多轮，例如进入页面、返回、旋转或替换 Fragment View；
3. 等待异步任务和已知动画结束；
4. 采集 heap dump；
5. 查找应已销毁的 Activity、Fragment View、Compose state（Compose 状态对象）、listener、callback 或 cache entry（缓存条目）；
6. 沿 GC Root path 找到生命周期更长的持有者；
7. 修复后重复同一脚本，并比较实例数和 retained graph（保留关系图）。

单个 Activity 仍存活不一定是泄漏，系统、输入法、动画和异步消息可能短期持有引用。证据应包含“对象已经越过预期生命周期”和“引用链在稳定状态仍存在”。

Android 8.0 / API 26 及以上，Bitmap pixel data（像素数据）位于 native heap。Java heap 中的 `Bitmap` 对象仍是追踪归属关系的入口，Android Studio heap dump 也可能在 Native Size 列显示关联的原生内存。只看 Java shallow size 会低估图片成本。

来源：[Android Studio Heap Dump 指南](https://developer.android.com/studio/profile/capture-heap-dump)

#### 3.3 分配 churn 与 retained leak 分开

对象创建速度很高、GC 后能回落，属于 allocation churn（大量短命对象造成的频繁分配）；对象沿异常引用链长期存活，属于 retained leak（对象保留型泄漏）。两者都可能让曲线升高，但定位工具不同：

- churn：记录 Java/Kotlin allocation callstack（分配调用栈）、GC 和帧时间；
- leak：使用 heap dump、dominator tree（支配树）与 GC root；
- 大数组或 Bitmap：同时核对 native size 和图片缓存策略；
- JNI global reference：结合 ART heap 与 native 调用栈检查持有者。

### 4. Native heap：分配归因与非法访问是两类问题

#### 4.1 heapprofd 用于分配调用栈

heapprofd 在 Android 10 及以上跟踪 `malloc/free`、`new/delete` 分配，并用抽样记录降低目标进程开销。user build（日常发布版本的系统镜像）只能分析声明为 `profileable` 或 `debuggable` 的 App。

下面的命令使用 Perfetto 仓库中的推荐脚本，按进程名启动 native heap profiling：

```bash
tools/heap_profile android -n com.example.app
```

以进程名启动时，已经运行的匹配进程和后续启动的匹配进程都可进入采样；需要启动期证据时，应先启动 profiler（分析器），再启动 App。多进程应用还要分别确认 `com.example.app:worker` 等进程名。结束采集后，在 Perfetto UI 中打开生成目录里的 `raw-trace` 原始轨迹文件。

四个常用视图回答不同问题：

| 视图 | 含义 |
|---|---|
| Unreleased malloc size | 采集窗口内已分配但尚未 `free` 的估算字节数 |
| Unreleased malloc count | 采集窗口内尚未 `free` 的估算分配次数 |
| Total malloc size | 窗口内全部分配的估算字节数，包含已经 `free` 的分配 |
| Total malloc count | 窗口内全部估算分配次数，包含已经 `free` 的分配 |

heapprofd 不能回溯采集开始前的历史分配，也默认看不到绕过默认分配器的直接 `mmap`、graphics buffer（图形缓冲区）和 GPU private allocation。采样间隔、buffer overrun（采集缓冲区溢出）、符号文件与进程启动方式都会影响结果。

来源：[Perfetto Native Heap Profiler](https://perfetto.dev/docs/data-sources/native-heap-profiler)

#### 4.2 heapprofd、allocator 与 resident memory 不能做简单减法

三类数字的范围逐步扩大：

```text
heapprofd
  采样到的 malloc/new 请求与 free

malloc_info / allocator statistics
  allocator 管理的 arena、cache 与仍持有的页面

Native Heap RSS / PSS
  已驻留页面，并受 page size、碎片、共享、swap 与采样时刻影响
```

`Native Heap RSS - heapprofd unreleased bytes` 不能直接命名为“碎片”。差值还可能来自未采样分配、启动前分配、allocator cache（分配器缓存）、对齐、页内空洞、直接 `mmap`、统计分类差异、ZRAM 和两个工具没有同时采样。

#### 4.3 malloc debug 只用于受控调试构建

普通 App 开发者应通过 debuggable APK 的 `wrap.sh` 启用 malloc debug。下面的脚本记录 native allocation backtrace（原生分配调用栈）：

```sh
#!/system/bin/sh
LIBC_DEBUG_MALLOC_OPTIONS=backtrace logwrapper "$@"
```

`wrap.sh` 仅适用于 API 27 及以上的 debuggable App，会改变进程启动与分配开销。它不能放进生产包。`libc.debug.malloc.program` 接受可执行文件名，不能填写 Java package（包名）；平台 root/userdebug 场景若要针对 App，使用官方文档给出的 `wrap.<package>` 属性或随 APK 打包的 `wrap.sh`。

来源：[NDK wrap.sh 指南](https://developer.android.com/ndk/guides/wrap-script)

#### 4.4 HWASan、GWP-ASan 与 heapprofd 的职责

| 工具 | 主要目标 | 适用方式 |
|---|---|---|
| heapprofd | 找分配调用栈、增长和 churn | profileable/debuggable App 或平台调试 |
| HWASan | 捕获 C/C++ 越界、use-after-free（释放后使用）和 double free（重复释放） | ARM64 测试构建；Android 14+ 可用 App `wrap.sh` |
| GWP-ASan | 抽样发现 heap use-after-free / overflow（堆越界） | Android 11+ 支持；Android 14+ 默认采用 Recoverable（可恢复）模式策略 |
| Malloc debug | guard（保护区）、backtrace、fill（填充值）等分配器调试 | debuggable App 或 root/userdebug |

ASan 仍可用于旧设备，但当前 NDK 指南已将它列为停止主动支持的方案；能使用 HWASan 时优先 HWASan。Sanitizer（内存错误检测器）会显著改变运行时间和内存开销，其测试数据不能作为普通 release 构建的基线。

来源：[NDK 内存错误调试与缓解](https://developer.android.com/ndk/guides/memory-debug)

### 5. Graphics、DMA-BUF 与 Bitmap

Android 17 的 AIDL `IMemtrack` 用来报告 smaps 无法完整追踪的设备相关内存。这里的 memtrack 是厂商 HAL 提供的设备内存记账接口，接口契约明确区分：

- `GRAPHICS + FLAG_SMAPS_UNACCOUNTED`：CPU/GPU 映射的 DMA-BUF PSS，并去除两组映射的重叠；
- `GL + FLAG_SMAPS_UNACCOUNTED`：指定 PID 的 GPU 私有分配；
- `pid = 0, type = GL`：系统级 GPU private memory；
- `OTHER + FLAG_SMAPS_UNACCOUNTED`：其他未进入 smaps 的设备内存。

HAL 必须避免不同 memtrack type（记账类别）重复记账，但设备是否支持某项查询、驱动能否准确归属到 PID，仍由产品实现决定。因此：

- `dumpsys meminfo` 的 Graphics 为 0 不证明没有 GPU 内存；
- Graphics 上升不能只从 Java heap dump 找 owner；
- SurfaceView、TextureView、ImageReader、MediaCodec、Camera 和 Vulkan 可能拥有不同的 buffer/layer 生命周期；
- Java `Bitmap` 引用释放后，还要等待图片库、GPU cache（GPU 缓存）和 renderer（渲染器）分别完成各自的释放流程。

源码核对：[`IMemtrack.aidl`](https://android.googlesource.com/platform/hardware/interfaces/+/refs/tags/android-17.0.0_r1/memtrack/aidl/android/hardware/memtrack/IMemtrack.aidl)

GPU 专项工具与 layer/buffer 追踪见 10.4 节；这里仅将 Graphics 从 Java/Native heap 口径中分离。

### 6. 建立可比较的基线

内存基线至少绑定以下维度：

| 维度 | 需要记录的值 |
|---|---|
| App | versionCode、build type（构建类型）、ABI、进程名 |
| 系统 | 设备型号、build fingerprint（系统构建指纹）、Android/API、page size |
| 场景 | 入口、操作脚本、循环次数、前后台状态 |
| 时间 | 进程启动后时长、采样点、采样工具 |
| 负载 | 账号数据量、图片规格、列表长度、网络响应 |
| 指标 | Java used/max、Native allocated、PSS、RSS、SwapPss、Graphics |

一份实用的采样脚本可以设置这些采样点：

1. 冷启动首屏稳定；
2. 目标页面第一次进入；
3. 相同操作完成固定轮数；
4. 返回初始页面并等待异步释放；
5. 进入后台；
6. 进程重新回到前台。

判断时看分布和形态：

- 每轮结束后的 retained set（回收后仍保留的对象集合）持续增长：分析持有者与引用链；
- Java used 上下波动但稳定回落：更接近正常 GC 或 churn；
- Native allocated 上升：用 heapprofd 找调用栈；
- PSS/RSS 上升而 Java/Native allocated 稳定：检查 `mmap`、代码页、线程栈、图形内存、DMA-BUF 和 allocator residency（分配器持有的驻留页面）；
- 前台高、后台回落：可能来自可回收缓存或图形资源生命周期；
- 进程退出：读取 `ApplicationExitInfo`，不要只用末条内存曲线推断原因。

阈值应来自同设备族、同场景的历史分布和产品风险预算。固定写成“PSS 增长 5% 即回归”或“Java heap 超过 85% 就 dump”会在不同设备、页面和数据量上制造误报。

#### 6.1 4 KB 与 16 KB page size 分组

Android 15 起支持使用 16 KB page size（内存页大小）的设备。页大小会影响 ELF（二进制文件格式）对齐、`mmap`、allocator page span（分配器跨越的页面范围）和驻留内存的计量单位。同一 APK 在 4 KB 与 16 KB 设备上的 PSS/RSS 基线可能不同。

基线处理规则：

- 记录 `getconf PAGE_SIZE`；
- 4 KB 与 16 KB 设备分组统计；
- 不用一个固定百分比从 16 KB 数据“还原”4 KB；
- native library 兼容性与内存回归分别判断；
- 同组内仍需固定系统构建版本、ABI 与输入数据。

官方文档中给出的总体内存变化来自特定测量集合，不能作为每个 App 的校正系数。

来源：[16 KB page size 支持指南](https://developer.android.com/guide/practices/page-sizes)

#### 6.2 用回落条件区分缓存、积压与泄漏

持续增长实验要比普通峰值测试多两个采样点：执行业务释放动作后的状态，以及主动收缩可重建资源后的状态。随后用同一输入再跑一轮，观察波峰、波谷和增长斜率是否重复。只在峰值抓一次 `dumpsys meminfo`，无法区分工作集扩大、缓存保留和生命周期错误。

| 增长来源 | 释放或收缩动作 | 仍需补充的证据 |
| --- | --- | --- |
| 业务 live set（仍在使用的数据集合） | 关闭页面、清空数据集或结束会话 | 对象类型、条目数、字节预算与业务容量是否同步变化 |
| 无上限缓存或队列积压 | 执行缓存裁剪、消费完队列或取消任务 | 缓存 owner、队列长度、命中收益和积压产生速度 |
| Java/Kotlin 对象泄漏 | 结束对象的业务生命周期并等待异步清理 | heap dump 中稳定存在的 GC Root 强引用路径，见上文第 3.2 节 |
| Native 未释放分配 | 关闭会话或执行配对释放 | heapprofd 的 live allocation 差分与符号化调用栈 |
| allocator 保留 | 确认 live allocation 已下降 | allocator 统计、`smaps` 与匿名驻留页；RSS 不立即回落不能单独命名为泄漏 |
| 直接 `mmap`、文件页或线程栈 | 关闭映射、结束线程并再次采样 | mapping 名称、创建者、线程数量和退出条件 |
| Surface、Image、Codec 或 DMA-BUF | 关闭资源并等待 consumer 释放引用 | 图形内存、layer/buffer 生命周期与相关进程的变化 |
| WebView 工作集 | 销毁实例并分别观察宿主与 renderer 进程 | provider 版本、renderer 生命周期、代码页、缓存与图形内存 |

缓存需要一份可执行协议，而不是“内存高时清一点”的约定。至少记录五项：任何输入下都不能超过的 hard limit（硬上限）、页面不可见或进入后台后的 shrink target（收缩目标）、统一计量单位、负责创建和裁剪的 owner，以及 size/hit/miss/eviction/rebuild cost（大小、命中、未命中、淘汰和重建成本）。`ActivityManager.getMemoryClass()` 只描述 ART 堆的近似上限，不能直接拿来当整个进程的缓存预算。

`LruCache.sizeOf()` 决定预算单位，`maxSize` 必须使用相同单位。条目离开 `LruCache` 后，Adapter、View、任务或其他集合仍可能保存引用；缓存计数下降不等于对象已经回收。`entryRemoved()` 也不是通用的 Bitmap `recycle()` 开关，只有所有权协议能证明没有其他使用者时，才可在淘汰回调中主动销毁资源。

长时间运行的音乐、导航、IM、RTC 等场景还要把运行时长纳入基线。环形缓冲区、历史数据、图片、地图瓦片、字幕和模型缓存分别设上限；音视频会话中的 Codec、Surface、Image 和原生 session 由同一个持有者成对关闭。每轮业务结束后比较 live set，而不是只看进程是否仍能运行。

### 7. 系统内存压力与 LMKD

Android 17 `lmkd` 可通过 PSI（Pressure Stall Information，压力停顿信息）事件感知 memory stall（内存压力造成的任务停顿），并结合 watermark（可用内存水位）、swap、workingset refault/thrashing（工作集页面频繁换入引起的抖动）、reclaim（页面回收）状态和产品属性决定是否回收进程。候选进程按 `oom_score_adj` 的保护级别扫描；配置或压力级别要求比较进程大小时，再从同一 adj 档选择内存占用较高的进程。

所以：

- App PSS 高不等于下一次一定被杀；
- 前台/可感知进程与 cached 进程的保护级别不同；
- victim（被选中回收的进程）不只由 PSS 决定；
- LMKD kill、kernel OOM、crash、ANR 和用户 force-stop 是不同退出原因；
- 设备厂商可调整 lmkd 属性与内存策略。

源码核对：

- [`lmkd.cpp`](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [`psi.c`](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/kernel/sched/psi.c)

#### 7.1 libpsi 只负责 PSI 事件通道

Android 17 的 `libpsi` 位于 `system/memory/lmkd/libpsi`。头文件把资源限定为 `PSI_MEMORY`、`PSI_IO`、`PSI_CPU`，并暴露 `PSI_SOME` / `PSI_FULL`、`psi_stats` 以及 monitor/parse 函数；库本身没有 victim 选择、`oom_score_adj` 扫描或 kill policy（查杀策略）。`lmkd` 调用 `init_psi_monitor(..., psi_window_size_ms * US_PER_MS)` 时没有显式传 `resource`，因此使用头文件默认值 `PSI_MEMORY`。[已验证: system/memory/lmkd/libpsi/include/psi/psi.h@android-17.0.0_r1#25][已验证: system/memory/lmkd/lmkd.cpp@android-17.0.0_r1#3435][来源: https://juejin.cn/post/7677254638325727242]

`init_psi_monitor()` 会先校验资源类型，再以 `O_WRONLY | O_CLOEXEC` 打开 `/proc/pressure/<resource>`，写入 `"some|full threshold_us window_us"`，成功后直接返回这个 fd。内核写入路径把 trigger（触发器）绑定到该打开文件；同一个 fd 再写第二个 trigger 会以 `-EBUSY` 拒绝。因此这个 fd 是“何时有压力”的事件通道，不是读取 `avg10/avg60/avg300/total` 的统计通道。[已验证: system/memory/lmkd/libpsi/psi.cpp@android-17.0.0_r1#36][已验证: kernel/sched/psi.c@android17-6.18-2026-06_r6#1569][来源: https://juejin.cn/post/7677254638325727242]

`register_psi_monitor()` 只用 `EPOLLPRI` 挂入 epoll，并把调用方传入的 `void* data` 放进 `epev.data.ptr`。内核 `psi_trigger_poll()` 在 trigger 的 `event` 标志从 1 被 `cmpxchg` 消费时返回 `EPOLLPRI`；按普通可读事件 `EPOLLIN` 监听会漏掉 PSI trigger 唤醒。[已验证: system/memory/lmkd/libpsi/psi.cpp@android-17.0.0_r1#86][已验证: kernel/sched/psi.c@android17-6.18-2026-06_r6#1489][来源: https://juejin.cn/post/7677254638325727242]

统计读取走另一组 fd：`psi_parse_mem()`、`psi_parse_io()`、`psi_parse_cpu()` 使用 `reread_file()` 读取 `/proc/pressure/*` 文本，`parse_psi_line()` 解析 `some/full avg10=... total=...`，其中 CPU 只解析 `some` 行。排查 `lmkd` 时应把 trigger 唤醒、统计快照和后续 kill decision（查杀决策）分开看。[已验证: system/memory/lmkd/lmkd.cpp@android-17.0.0_r1#2093][已验证: system/memory/lmkd/libpsi/psi.cpp@android-17.0.0_r1#109][来源: https://juejin.cn/post/7677254638325727242]

内核侧参数边界也要按目标内核核对：Android common kernel `android17-6.18-2026-06_r6` 拒绝 `window_us == 0` 或超过 10s，拒绝 `threshold_us == 0` 或 threshold 大于 window；未特权写入还要求 window 是 2s 的倍数。`lmkd` 的默认 PSI 窗口为 1000 ms，并在 PSI 事件后按 10/100 ms 间隔轮询一个窗口，因为同一 trigger 在内核中至多每个窗口通知一次。不要把其他内核分支或博客中的窗口下限直接写成 Android 17 通用结论。[已验证: kernel/sched/psi.c@android17-6.18-2026-06_r6#1336][已验证: kernel/sched/psi.c@android17-6.18-2026-06_r6#509][已验证: system/memory/lmkd/lmkd.cpp@android-17.0.0_r1#118][来源: https://juejin.cn/post/7677254638325727242]

#### 7.2 用 `ApplicationExitInfo` 补齐进程退出上下文

下面的代码读取当前包最近的退出记录：

```kotlin
val exitRecords = activityManager.getHistoricalProcessExitReasons(
    context.packageName,
    0,
    16,
)

for (record in exitRecords) {
    Log.i(
        "ExitMemory",
        "reason=${record.reason}, importance=${record.importance}, " +
            "pssKb=${record.pss}, rssKb=${record.rss}, " +
            "timestamp=${record.timestamp}",
    )
}
```

`getPss()` 与 `getRss()` 是系统上一次采样值，单位 kB；进程在采样前退出时可能为 0，该值也不代表退出瞬间的内存。应结合 `reason`（退出原因）、`subreason`（细分原因）、importance（进程重要性）、描述、trace 和自定义 state summary（状态摘要）判断。

应用还可以在低频业务状态切换时写入最多 128 bytes（字节）的非敏感摘要：

```kotlin
val state = "screen=checkout;phase=confirm"
    .toByteArray(StandardCharsets.UTF_8)
activityManager.setProcessStateSummary(state)
```

系统可能限制该 API 的调用频率，过度调用会抛出 `RuntimeException`。摘要用于退出分析，不用于恢复 UI，也不能包含账号、订单、位置等敏感信息。

源码核对：[`ApplicationExitInfo.java`](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/app/ApplicationExitInfo.java#912)

### 8. 线上监控只采集低风险证据

线上内存监控不应远程触发 heap dump、malloc debug 或 sanitizer。适合收集的内容包括：

- 进程、页面/场景枚举和前后台状态；
- Java used/max；
- 低频采集本进程的 PSS/RSS 与摘要分类；
- native allocated；
- page size、ABI、device/build、App 版本；
- trim callback（内存回收提示回调）、退出原因和最近的非敏感状态摘要；
- OOM、native crash 与 LMKD 相关的聚合事件。

采样时机根据业务选择：

- 场景进入和退出；
- 固定生命周期节点；
- 内存增长速度异常时增加一份低成本快照；
- 进程下次启动时读取历史退出记录；
- 实验组与基线组使用相同采样策略。

采样本身会排队、读取 procfs（`/proc` 进程信息文件系统）或调用 Binder。周期由设备开销实验确定，不使用通用的“30—60 秒”。`getProcessMemoryInfo()` 的系统缓存也使更短周期未必产生新数据。

隐私与稳定性要求：

- 不上传 heap 内容、对象字符串、文件路径、图片或业务 payload（载荷数据）；
- state summary 使用枚举或短 ID，不写用户标识；
- 采样失败返回 unknown，不循环重试；
- 单位写进字段名；
- 多进程分别记录 PID、进程名和角色；
- OOM 前末次样本只当上下文，不当死亡瞬间证据。

### 9. 按现象选工具

| 现象 | 下一步工具 | 需要证明的事 |
|---|---|---|
| Java used 与实例数持续增长 | Heap dump / dominator / GC root | 哪个长生命周期持有者保留对象 |
| Java used 回落但 GC 很密 | ART allocation profiling / Perfetto | 哪些调用栈制造 churn |
| Native allocated 持续增长 | heapprofd | 哪些 malloc/new 调用栈未释放 |
| Native RSS 高于 allocator 统计 | smaps、malloc_info、mmap trace | 缓存、碎片、直接映射或 swap 哪项成立 |
| Graphics 增长 | memtrack、SurfaceFlinger layer、GPU 专项工具 | 哪个 Surface、buffer 或 GPU 资源持有者未释放 |
| PSS/RSS 增长但 heap 稳定 | meminfo 分类、threads、maps、graphics | 增量属于 code、stack、mmap、共享页还是设备内存 |
| 进程消失 | `ApplicationExitInfo`、系统日志、LMKD 事件 | 退出原因、保护级别与上次采样上下文 |
| Native 非法访问 | HWASan / GWP-ASan / Malloc debug | 越界、use-after-free 或 double free 的访问栈 |

### 10. 交付前检查表

- [ ] 每个指标都标明单位、来源、进程和采样时刻。
- [ ] PSS 没有与 `memoryClass` 或 `largeMemoryClass` 计算比例。
- [ ] Java heap、native allocator、resident pages 和 Graphics 分开。
- [ ] Heap dump 结论包含预期生命周期与 GC root。
- [ ] heapprofd 结论注明采样窗口、interval（采样间隔）、符号和未覆盖的 `mmap`/graphics。
- [ ] Native RSS 与 heapprofd 的差值没有直接写成碎片。
- [ ] malloc debug 只用于 debuggable/root 受控环境。
- [ ] Bitmap 在 API 26+ 的 pixel data 按 native 归属关系分析。
- [ ] memtrack 缺失或为 0 时，没有断言 GPU 内存为 0。
- [ ] 4 KB 与 16 KB page size 使用不同基线分组。
- [ ] LMKD 判断包含 PSI、reclaim、swap/thrashing、adj 与设备配置。
- [ ] `ApplicationExitInfo` 的 PSS/RSS 被标为上次采样。
- [ ] 线上数据不含 heap 内容和敏感业务信息。

---

### 延伸阅读

- [4.1 Android 与 Linux 内存管理全景](../../part1-fundamentals/ch04-memory/01-android-linux-memory-overview.md)：统计口径、物理页与回收机制。
- [4.2 ART Heap、GC 与后台维护调度](../../part1-fundamentals/ch04-memory/02-art-heap-gc-maintenance.md)：Java 堆、GC 与存活对象的关系。
- [4.3 lmkd、Cached App Freezer 与内存压力治理](../../part1-fundamentals/ch04-memory/03-lmkd-freezer-memory-pressure.md)：系统压力、进程优先级与后台状态。
- [23.2 内存泄漏检测与治理](../../part5-app/ch23-memory-practice/02-memory-leak-governance.md)：引用链与生命周期修复。
- [14.1 Perfetto 入门、Trace 抓取与可靠性](../../part3-tools/ch14-perfetto/01-perfetto-intro-capture-reliability.md)：采集配置、数据源与 trace 完整性。


## 从异常曲线到分配责任

基线模型用于提出假设，案例需要继续证明增长来自泄漏、缓存、抖动、图形资源还是系统共享内存。

这一节复核四个公开案例。每个数字都来自原文所述环境，用于还原取证过程，不宜直接写进其他产品的阈值或收益目标。Android 平台机制按 `android-17.0.0_r1` 核对，内存回收机制按 `android17-6.18-2026-06_r6` 核对。旧设备案例保留原系统、ABI 和驱动条件。

| 案例 | 主要内存域 | 决定性证据 | 原文公布的结果 |
| --- | --- | --- | --- |
| 低内存导致冷启动退化 | 系统回收、文件页、I/O | 主线程 D 状态（不可中断睡眠）时长、`kswapd0`、进程终止与重启记录 | 原文未公布参数调整后的 A/B 数据 |
| 线上 Hprof 归因 Java OOM | Java 堆 | dominator tree（支配树）、Retained Size、GC Root 路径 | Helo 与美篇均有双月数据，口径见案例二 |
| PowerVR `renderD128` 映射增长 | GPU 用户态驱动、虚拟地址空间 | `syscall(__NR_mmap2)`、`KEGLGetPoolBuffers`、buffer pool（缓冲池）阈值 | 受影响机型实验的 OOM 崩溃率下降近 50% |
| MemoryThrashing 差分采样 | 原案例为 iOS Objective-C 对象 | 连续样本间的 alloc/dealloc（分配/释放）与存活实例差值 | 发布时处于测试环境监控，未公布线上 OOM 降幅 |

### 案例一：低内存导致冷启动等待 Block I/O

#### 现象与数据边界

历史文章对比了低内存与正常内存下的冷启动 trace。低内存样本的 Running（实际在 CPU 上执行）时间为 682 ms，正常样本为 624 ms；两者的 CPU 执行时间接近。差距集中在主线程不可中断睡眠：低内存样本的 `Uninterruptible Sleep | WakeKill - Block I/O`（块设备 I/O 唤醒前的不可中断等待）与普通 Uninterruptible Sleep 合计约 750 ms，正常样本约 130 ms。正常样本从启动到首帧约 1.22 s。

这些数字只描述该次 trace。单看总启动耗时，很容易把问题归到主线程代码；线程状态给出了另一条线索：额外时间主要用于等待内核和存储路径。

#### 证据怎样形成完整链条

诊断需要把四类时间对齐：

1. 在 Perfetto 中圈出启动区间，比较主线程 Running、Runnable（可运行但在等待 CPU）、Sleeping 与 D 状态。
2. 展开 D 状态对应的内核调用栈，确认是否等待文件页、块设备或文件系统锁。
3. 在同一时间窗检查 `kswapd0`、内存回收 tracepoint（跟踪点）、`meminfo`、`vmstat`、swap/ZRAM 和 PSI（资源压力停顿信息）。
4. 检查 `lmkd` 与 ActivityManager 事件，确认同一进程是否在短时间内反复被终止，又被业务或系统重新启动。

`mm/vmscan.c` 中的回收路径解释了 `kswapd` 与直接回收的执行位置，`include/trace/events/vmscan.h` 提供回收 tracepoint 定义。Android 17 的 `lmkd.cpp` 使用 PSI 监视器感知 stall（资源停顿），并结合进程重要性和内存状态选择要终止的进程。两部分要放在同一时间轴上观察：回收持续繁忙、前台线程进入 D 状态和终止进程记录同时出现，才足以支持“系统内存压力拖慢前台”的判断。

#### 根因判断

该案例的证据支持三段因果关系：

- 内存水位偏低时，后台回收更活跃，文件页更容易被回收。
- 启动读取 odex（预编译字节码文件）、资源或配置时发生缺页，主线程等待存储 I/O，D 状态时长增加。
- 缓存进程反复终止与重启会继续消耗 CPU、I/O 与内存，使压力时间窗延长。

主线程与 `kswapd0` 同核运行可能增加竞争，但一次 trace 中的同核现象还不足以证明调度策略存在缺陷。分析报告应分别列出“trace 直接观察到的事实”和“基于内核机制的解释”。

#### 修复与验证

原文给出了调高 `extra_free_kbytes`（额外预留空闲内存）等历史建议。它们不能直接迁移到 Android 17 产品：内核回收参数、ZRAM、存储延迟、PSI 阈值和 `lmkd` 策略互相影响，单项调大也可能带来更多后台回收或更高的进程重启率。

系统侧修复应以同场景 A/B 为准：

- 对比压力前后的 PSI `some/full`、direct reclaim（分配线程同步回收）、`kswapd` CPU、major fault（需要从存储读取的缺页）和块 I/O 延迟。
- 核对 `lmkd` 每次选择的进程、释放量及后续重启，减少没有实际回收收益的终止—重启循环。
- 分设备内存档位校准回收、ZRAM 与杀进程策略，并用前台帧时间、启动耗时和后台存活率共同验收。

App 侧可在 `TRIM_MEMORY_UI_HIDDEN` 或 `TRIM_MEMORY_BACKGROUND` 到来时释放可重建缓存。Android 14（API 34）起，`TRIM_MEMORY_RUNNING_*`、`MODERATE`、`COMPLETE` 不再投递；Android 15（API 35）又将相关常量标为 deprecated。App 无法依靠旧 trim level 推断实时系统压力，也不应在每次回调中同步执行大规模清理。

原文没有给出参数调整后的量化结果。复用这个案例时，可引用 trace 前后的 750 ms 与 130 ms，不能补写不存在的修复收益。

### 案例二：用线上 Hprof 找到 Java OOM 的持有者

#### 现象

Java OOM 常落在 Bitmap 分配、字符串构造或数组扩容等位置。该位置只表示本次分配失败，无法回答“此前的堆被谁长期占用”。字节跳动 Client Infra 的公开案例采用线上 Hprof（Java 堆快照格式），把分析对象从崩溃点转向对象持有关系。

#### 采集与分析

公开方案由客户端采集、服务端恢复与自动分析组成：

- 客户端可在 OOM 或可配置的内存高水位采集 Hprof，使用子进程减轻 dump（导出堆快照）对交互线程的影响。
- Tailor（该方案的 Hprof 裁剪工具）在 native 层移除字符串内容、Bitmap 像素等分析无需保留的数据。原文公布的头条样本平均文件大小从 355 MB 降至 44 MB。
- 服务端重建引用图和支配树，计算 Shallow Size（对象自身大小）、Retained Size（对象不可达后可一并回收的估算大小）与 GC Root 路径，再按泄漏类、持有业务代码或大对象类聚合。
- 混淆后的类名和引用路径经 Retrace（根据映射文件恢复原始符号）还原，问题才能分派给代码所有者。

线上 Hprof 可能包含账号、文本和业务对象。采集前要有用户授权与合规评审，上传链路需要加密、限流、访问审计和过期删除。裁掉字符串内容并不能自动覆盖所有敏感字段。

#### 根因证据

原文展示的按类聚合样本中，`ArticleCell` 有 364 个实例，总 Retained Size 为 51.29 MB，其中 280 个由 `MainActivity` 持有。该数据把排查点从 OOM 栈移到 `MainActivity` 的引用所有权。

修复动作要服从引用语义：

- 页面退出后仍被任务、监听器或容器持有时，取消任务、解除注册并清理页面所有者。
- 数量符合业务需求但 Retained Size 过大时，减少单对象负载或限制集合容量。
- 缓存需要保留时，明确容量、失效条件与低内存行为；`WeakHashMap` 只弱持有 key，无法代替缓存策略。
- Android 8.0（API 26）起 Bitmap 像素位于 native heap。生命周期正常的 Bitmap 通常交给 GC 与 `NativeAllocationRegistry`（Java 对象关联原生分配的运行时登记机制）管理；不要把批量调用 `Bitmap.recycle()` 写成通用修复。显式提前回收还可能让仍在绘制的调用方访问已释放像素。

修复后应重放同一场景并再次 dump，验证实例数量、GC Root 路径与 Retained Size 同时下降。只看 Java heap 的峰值下降，无法区分引用修复、采样时机变化和 GC 调度差异。

#### 原文结果与 Android 17 增量

原文公布了两组产品数据：

- Helo 在一个双月内处理了 80% 以上的 Java OOM 问题，次日留存增长 2% 以上。
- 美篇在一个双月内 Java OOM 降低 80%，用户卡顿率也下降 80%。

这些是来源文章中的平台客户数据，不能推导出任意 App 接入 Hprof 后会获得同等收益。文章没有披露完整实验设计，也没有把收益分摊到某个缓存改动。

Android 17（API 37）的 `ProfilingTrigger.TRIGGER_TYPE_OOM` 可在 OOM 时请求 Java heap dump。App 安装自定义 `UncaughtExceptionHandler` 后，仍须调用默认 handler，否则 OOM trigger（触发器）不会生效。`TRIGGER_TYPE_ANOMALY` 可由系统异常检测触发相应 artifact（诊断文件）。两类触发均受系统限流，结果也可能为空；它们只补充采集入口，引用图、隐私处理、聚合和修复验证仍由诊断系统完成。

### 案例三：PowerVR buffer pool 长期保留 `renderD128` 映射

#### 环境与复现

原案例集中在华为 Android 10、联发科芯片、PowerVR GPU 与 32 位 `armeabi-v7a` 进程，少量样本覆盖 Android 8.1、9、11 和 12。OOM 发生时，GPU render node（渲染设备节点）`/dev/dri/renderD128` 的映射接近 1 GB，32 位进程的虚拟地址空间被大量占用。

团队在华为畅享 10e（Android 10）做了对照实验：新增 10 个普通背景 View 时映射无明显变化；给新增 View 设置 `alpha=0.5` 后，每个 View 对应的 `renderD128` 映射约增加 25 MB。这是特定设备、驱动和复现工程的数据，不能外推到其他 GPU。

#### 从缺失的 Hook 记录找到映射入口

常见 `mmap`、`mmap64`、`mremap`、`__mmap2` Hook（运行时拦截）没有记录到这批映射，`ioctl` 记录也无法解释增长。继续反汇编 vendor（厂商）库后，团队发现 `libsrv_um.so` 直接调用 `syscall`，系统调用号对应 32 位 ARM 的 `mmap2`。

随后只拦截 `libsrv_um.so` 与 `gralloc.mt6765.so` 对 `syscall` 的调用，映射记录出现。这个证据修正了“映射完全发生在内核驱动内部”的早期猜测：PowerVR 用户态库绕过了 libc 的 `mmap` 符号，直接进入系统调用。

调用栈继续指向 `libIMGegl.so` 的 `KEGLGetPoolBuffers`。一次增长会连续调用五次 `PVRSRVAcquireCPUMapping`，五类 buffer 合计约 25 MB，与 View 实验的增量吻合。绘制结束时，`KEGLReleasePoolBuffers` 只把 buffer 标为空闲，没有对应调用 `PVRSRVReleaseCPUMapping`。这些映射可在 EGL surface（EGL 绘制表面）或 `CanvasContext` 销毁路径释放，因此文章将其定性为 buffer pool 长期保留；它不同于任何释放路径都不存在的永久泄漏。

#### 根因与历史修复

反汇编显示 pool 为每类 buffer 设置 `buffer_limits`。测试设备原值为 50，映射峰值约 1.25～1.3 GB；调为 20 时峰值约 530 MB，调为 10 时约 269 MB。团队针对已识别的 vendor 版本修改该阈值。来源文章公布的受影响机型实验中，OOM 崩溃率下降近 50%，观察期间未再因 `renderD128` 问题阻断版本发布。

这是针对非公开 vendor 实现的历史干预，不能作为通用 App 方案。其他厂商、驱动版本或进程位数可能使用完全不同的 pool 数据结构；错误 Hook 私有函数也可能破坏正在使用的 GPU 资源。

产品侧更稳妥的处理顺序是：

- 先按设备型号、SoC、GPU、OS、驱动与 ABI 聚类，确认问题是否只出现在少量设备组合中。
- 监控 `/proc/self/maps` 或 smaps 中 `renderD128` 映射，区分虚拟地址耗尽与物理驻留增长。
- 在受影响设备上减少使用能够稳定触发映射增长的渲染组合，必要时仅对这些设备降低动画或复杂效果。
- 推进 64 位进程可缓解 32 位地址空间耗尽，但不会减少 buffer 的物理内存成本。
- 将复现工程、映射增长曲线和 vendor 调用栈交给 SoC、GPU 或 ROM 厂商修复。

#### Android 17 源码边界

Android 17 HWUI 的 `RenderProperties::promotedToLayer()` 会在 alpha 位于 `(0, 1)` 且节点报告 overlapping rendering（内容存在重叠绘制）时把节点提升为独立 layer（图层）；`RenderNode::pushLayerUpdate()` 负责创建或更新对应图层。该源码能解释 alpha 组合为何可能进入额外的图层路径，不能证明 Android 10 的 PowerVR pool 行为仍存在于 Android 17。

`hasOverlappingRendering()` 返回 `false` 只适合内容没有重叠混合的自定义 View。错误返回可能改变视觉结果。`LAYER_TYPE_NONE` 也不能关闭 alpha 引起的自动图层提升。渲染优化应以 Frame Timeline（帧时间线）、GPU 内存和画面对比共同验收。

### 案例四：保留 MemoryThrashing 的差分思路与平台边界

#### 原案例运行在 iOS

MemoryThrashing 原文来自抖音直播 iOS 团队。实现通过 Objective-C Runtime Hook（运行时拦截）`alloc`、`dealloc`，统计各 Class 的分配、释放和存活实例数；它没有使用 Android 的 `Runtime.totalMemory()`、Java heap 或 ART 分配接口。

工具按多个时间点采样，对相邻样本做对象数量差分，定位两类异常：

- **驻留堆积**：原文样本在两个采样周期之间新增 234,024 个对象，样本末仍有 238,800 个 `LivexxxBigDataRead` 实例，占用 10.9 MB。
- **临时对象洪峰**：开播特效识别人脸后频繁创建轮廓模型；小于 5 秒的采样周期内，临时对象增量峰值约 60,000，累计分配超过百万次。

第二类对象可能很快释放，却会增加 CPU 与 allocator（内存分配器）压力；第一类需要继续查询引用关系，区分业务保留、缓存超限和泄漏。对象数量差分只能告诉工程师“哪类对象增长”，不能独立回答“谁在持有”。

原文明确列出限制：只覆盖 Objective-C 对象、不能分析多个内存区域、没有完整引用图，Hook 还会影响方法缓存。文章发布时工具已部署到测试环境，线上部署仍在规划中，因此没有可引用的线上 OOM 降幅或定位耗时改善数据。

#### Android 上如何复用

Android 侧可保留“连续样本差分 + 异常时加深采集”的设计，采集器必须按内存域选择：

| 内存域 | 轻量信号 | 深入证据 |
| --- | --- | --- |
| Java/Kotlin 对象 | heap 使用量、GC 次数与停顿、受控场景的对象分配样本 | Java heap dump、实例数差分、GC Root 路径 |
| Native malloc | RSS/PSS 分类、`anon:libc_malloc`、分配速率 | heapprofd 调用栈与分配生命周期 |
| 图形缓冲区 | DMA-BUF（设备间共享缓冲区）、GPU 驱动映射、Surface 数量 | `dmabuf_dump`、smaps、Perfetto graphics 轨道、厂商工具 |
| 文件映射与线程栈 | maps 分类、线程数、地址空间余量 | smaps、线程创建栈、映射调用栈 |

业务探针（埋入业务流程的轻量采样代码）只采集总 PSS 时，Java 临时对象、native buffer 与 GPU 映射会混在一条曲线上。更可靠的报警条件由“场景 + 内存域 + 增长速率 + 回落情况”组成，阈值应来自设备档位和同场景分位数，不能采用来源不明的时间与容量数值。

Android 15（API 35）提供 app-driven（由 App 主动请求的）`ProfilingManager.requestProfiling()`。Android 16（API 36）加入触发器注册。Android 17（API 37）增加 OOM、anomaly（异常）和 cold-start（冷启动）等 trigger。OOM trigger 发生在 OOM 时，用于申请 Java heap dump，无法替代 OOM 前的突增探针。采集结果受限流和系统策略约束，线上设计仍要处理“触发后没有 artifact（诊断文件）”的情况。

当差分指出某一类实例异常增长时，再采集 heap dump 或 allocation profile；当增长落在 native 或 graphics 域时，切换到 heapprofd、smaps 或图形工具。这样可以保留 MemoryThrashing 的低成本发现能力，同时避免把 iOS Runtime 实现误写成 Android 方案。

### 四个案例共同说明什么

#### OOM 栈回答不了历史占用

OOM 栈记录失败的分配点。要说明此前的内存由谁占用，还需查看 Java Hprof 的 Retained Size、native 分配调用栈、GPU 映射来源和进程地址空间分布。

#### 同一条“内存上涨”曲线可能属于不同机制

Java 引用泄漏、短命对象洪峰、malloc 堆积、GPU pool、文件映射和系统回收压力需要不同证据。排查入口应从 `dumpsys meminfo`、smaps 和 Perfetto 建立内存域分类，再进入专用工具。

#### 发布数字要保留实验上下文

80%、近 50%、355 MB 到 44 MB 都是来源文章在特定产品、周期或设备上的数据。文章复用这些数字时，应同时写明产品、周期、设备或指标口径。缺少结果数据的案例保持空白结论，比补一个“明显改善”更可靠。

#### 驱动与 ROM 问题先做设备聚类

当问题集中在一个 SoC、GPU、OS 与 ABI 组合时，设备聚类结果本身就是证据。通用代码修改可能扩大需要回归测试的范围；针对少量设备复现、定向规避和厂商修复更适合此类故障。

### 复盘清单

- 现象对应 Java heap、native heap、graphics、mmap、线程栈还是整机压力？
- 效果数字来自本项目实验、公开案例，还是尚未验证的预期？
- 低内存 trace 是否同时包含线程状态、回收、PSI、I/O 与 `lmkd` 事件？
- Hprof 是否记录 Retained Size、GC Root 路径、版本和场景？
- 32 位 OOM 是否同时检查了地址空间余量与 RSS？
- vendor 故障是否按设备、SoC、GPU、驱动、OS 和 ABI 聚类？
- 突增探针是否按内存域采样，并为缺失 artifact 设计回退路径？
- 修复后是否重放同一场景，比较同口径的峰值、回落速度、帧时间和崩溃率？

### 相关章节

- **10.1 本文**：内存域分类、基线、持续增长、`dumpsys meminfo`、smaps、Perfetto 与 heapprofd。
- [23.2 内存泄漏检测与治理](../../part5-app/ch23-memory-practice/02-memory-leak-governance.md)：引用所有权、GC Root 与生命周期修复。
- **10.2 低内存对系统性能的影响**：回收、PSI、`lmkd`、ZRAM 与前台性能。
- **10.3 内存抖动与频繁 GC**：分配速率、GC 停顿和短命对象。
- **10.4 GPU 与图形内存统计、归因与诊断**：DMA-BUF、GPU 映射与图形缓冲区。
- **4.3 Low Memory Killer**：Android 17 userspace `lmkd` 路径。
- **7.2 典型场景分析**：从线程状态和关键路径解释卡顿。


## 参考资料

- [Android 中的卡顿丢帧原因概述——低内存篇](https://www.androidperformance.com/2019/09/18/Android-Jank-Due-To-Low-Memory/)
- [Android-PSI 详解：libpsi 源码解析](https://juejin.cn/post/7677254638325727242)
- [字节跳动应用性能监控帮助客户 Java OOM 崩溃率下降 80%](https://mp.weixin.qq.com/s?__biz=Mzg2NTYyMjYxNg==&mid=2247486007&idx=1)
- [抖音 renderD128 系统级疑难 OOM 分析与解决](https://mp.weixin.qq.com/s?__biz=MzI1MzYzMjE0MQ==&mid=2247514363&idx=1)
- [MemoryThrashing：抖音直播解决内存抖动实践](https://mp.weixin.qq.com/s?__biz=MzI1MzYzMjE0MQ==&mid=2247496677)
- [Android Developers：内存管理概览](https://developer.android.com/topic/performance/memory-overview)
- [Android Developers：ProfilingManager](https://developer.android.com/reference/android/os/ProfilingManager)
- [Android Developers：ProfilingTrigger](https://developer.android.com/reference/android/os/ProfilingTrigger)
- [Perfetto：heapprofd](https://perfetto.dev/docs/data-sources/native-heap-profiler)
- [AOSP `ComponentCallbacks2.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/core/java/android/content/ComponentCallbacks2.java)
- [AOSP `RenderProperties.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/RenderProperties.h)
- [AOSP `RenderNode.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/frameworks/base/+/refs/tags/android-17.0.0_r1/libs/hwui/RenderNode.cpp)
- [AOSP `ProfilingTrigger.java`（android-17.0.0_r1）](https://android.googlesource.com/platform/packages/modules/Profiling/+/refs/tags/android-17.0.0_r1/framework/java/android/os/ProfilingTrigger.java)
- [AOSP `lmkd.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/lmkd.cpp)
- [AOSP `libpsi/psi.cpp`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/libpsi/psi.cpp)
- [AOSP `libpsi/include/psi/psi.h`（android-17.0.0_r1）](https://android.googlesource.com/platform/system/memory/lmkd/+/refs/tags/android-17.0.0_r1/libpsi/include/psi/psi.h)
- [Android Common Kernel `mm/vmscan.c`（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/mm/vmscan.c)
- [Android Common Kernel `vmscan.h` tracepoints（android17-6.18-2026-06_r6）](https://android.googlesource.com/kernel/common/+/refs/tags/android17-6.18-2026-06_r6/include/trace/events/vmscan.h)
